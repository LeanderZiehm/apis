import time
from typing import List, Dict, Optional
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os 
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {GROQ_API_KEY}",
}


# -----------------------------
# Model Availability Management
# -----------------------------
class ModelState:
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.disabled_until: Optional[float] = None

    def is_available(self) -> bool:
        if self.disabled_until is None:
            return True
        if time.time() >= self.disabled_until:
            self.disabled_until = None
            print(f"[INFO] Model {self.model_id} is usable again")
            return True
        return False

    def disable(self, retry_after_seconds: int):
        self.disabled_until = time.time() + retry_after_seconds
        print(
            f"[WARN] Model {self.model_id} rate-limited. "
            f"Disabled for {retry_after_seconds}s"
        )


class ModelPool:
    def __init__(self, models: List[str]):
        self.models_order: List[str] = models.copy()
        self.models: Dict[str, ModelState] = {m: ModelState(m) for m in models}

    def get_available_models(self) -> List[str]:
        return [m for m in self.models_order if self.models[m].is_available()]

    def all_disabled(self) -> bool:
        return not any(m.is_available() for m in self.models.values())

    def reorder(self, new_order: List[str]):
        # Keep only models that exist
        filtered_order = [m for m in new_order if m in self.models]
        # Add any models not in new_order at the end
        remaining = [m for m in self.models_order if m not in filtered_order]
        self.models_order = filtered_order + remaining
        print(f"[INFO] New model order: {self.models_order}")


# -----------------------------
# Groq Client
# -----------------------------
class RateLimitError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after


class GroqClient:
    def __init__(self, model_pool: ModelPool):
        self.model_pool = model_pool

    def chat(self, messages: List[dict], model: Optional[str] = None) -> dict:
        models_to_try = [model] if model else self.model_pool.get_available_models()
        if not models_to_try:
            raise HTTPException(status_code=503, detail="All models are currently rate-limited")

        last_error = None

        for model_id in models_to_try:
            model_state = self.model_pool.models[model_id]
            try:
                response = self._call_model(model_id, messages)
                return response
            except RateLimitError as e:
                model_state.disable(e.retry_after)
                last_error = e

        raise HTTPException(status_code=429, detail="Rate limit exceeded for all available models")

    def _call_model(self, model_id: str, messages: List[dict]) -> dict:
        payload = {"model": model_id, "messages": messages}
        print(payload)
        response = requests.post(GROQ_API_URL, headers=HEADERS, json=payload, timeout=30)

        if response.status_code == 429:
            retry_after = int(response.headers.get("retry-after", "5"))
            raise RateLimitError(retry_after)

        if not response.ok:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return response.json()


# -----------------------------
# FastAPI Layer
# -----------------------------
app = FastAPI(title="Groq Auto Model Switcher")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


all_models = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant",
]

model_pool = ModelPool(models=all_models)
groq_client = GroqClient(model_pool)


# -----------------------------
# Pydantic Schemas
# -----------------------------
class ChatRequestManuel(BaseModel):
    message: str
    model: str
    system_prompt: Optional[str]

class ChatRequestAuto(BaseModel):
    message: str
    system_prompt: Optional[str]

    class ConfigDict:
        json_schema_extra = {
            "example": {
                "message": "hi",
                "system_prompt": "You are a helpful assistant"
            }
        }


class ReorderRequest(BaseModel):
    new_order: List[str]
    class ConfigDict:
        json_schema_extra = {
            "example": {
                "new_order": [
                    "leander2 llama-3.3-70b-versatile",
                    "openai/gpt-oss-120b",
                    "llama-3.1-8b-instant"
                ]
            }
        }


@app.get("/", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="OCR API Docs")



# def chat 

# -----------------------------
# Endpoints
# -----------------------------
@app.get("/models/available")
def get_available_models():
    return {"available_models": model_pool.get_available_models()}





@app.post("/chat/auto")
def chat_auto(request: ChatRequestAuto):
    messages = [{ "role": "system", "content": request.system_prompt },{"role": "user", "content": request.message}]
    response = groq_client.chat(messages)
    return {
        "model_used": response["model"],
        "response": response["choices"][0]["message"]["content"],
    }


@app.post("/chat/manual")
def chat_manual(request: ChatRequestManuel):
    if not request.model or request.model not in all_models:
        raise HTTPException(status_code=400, detail="Invalid or missing model")

    messages = [{ "role": "system", "content": request.system_prompt },{"role": "user", "content": request.message}]
    response = groq_client.chat(messages, model=request.model)
    return {
        "model_used": response["model"],
        "response": response["choices"][0]["message"]["content"],
    }


@app.post("/models/reorder")
def reorder_models(request: ReorderRequest):
    model_pool.reorder(request.new_order)
    return {"new_order": model_pool.models_order}


@app.get("/models/best")
def get_best_model():
    """
    Returns the user's favorite model (first in the priority list)
    along with its availability status.
    """
    if not model_pool.models_order:
        return {"error": "No models configured"}

    best_model_id = model_pool.models_order[0]
    best_model_state = model_pool.models[best_model_id]

    return {
        "model": best_model_id,
        "available": best_model_state.is_available()
    }


@app.get("/models/best-available")
def get_best_available_model():
    """
    Returns the highest-priority model that is currently available.
    """
    available_models = model_pool.get_available_models()
    if not available_models:
        return {"error": "No models currently available"}

    best_available_model = available_models[0]
    return {
        "model": best_available_model,
        "available": True
    }


