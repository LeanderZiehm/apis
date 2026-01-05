import time
from typing import List, Dict, Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os 

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
        self.models: Dict[str, ModelState] = {
            m: ModelState(m) for m in models
        }

    def get_available_models(self) -> List[ModelState]:
        return [m for m in self.models.values() if m.is_available()]

    def all_disabled(self) -> bool:
        return not any(m.is_available() for m in self.models.values())


# -----------------------------
# Groq Client
# -----------------------------
class GroqClient:
    def __init__(self, model_pool: ModelPool):
        self.model_pool = model_pool

    def chat(self, messages: List[dict]) -> dict:
        available_models = self.model_pool.get_available_models()

        if not available_models:
            raise HTTPException(
                status_code=503,
                detail="All models are currently rate-limited",
            )

        last_error = None

        for model_state in available_models:
            try:
                response = self._call_model(
                    model_state.model_id, messages
                )
                return response
            except RateLimitError as e:
                model_state.disable(e.retry_after)
                last_error = e

        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for all available models",
        )

    def _call_model(self, model_id: str, messages: List[dict]) -> dict:
        payload = {
            "model": model_id,
            "messages": messages,
        }

        response = requests.post(
            GROQ_API_URL,
            headers=HEADERS,
            json=payload,
            timeout=30,
        )

        if response.status_code == 429:
            retry_after = int(
                response.headers.get("retry-after", "5")
            )
            raise RateLimitError(retry_after)

        if not response.ok:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text,
            )

        return response.json()


class RateLimitError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after


# -----------------------------
# FastAPI Layer
# -----------------------------
app = FastAPI(title="Groq Auto Model Switcher")

all_models=[
       "openai/gpt-oss-120b",
        "llama-3.3-70b-versatile"
    ]

model_pool = ModelPool(
    models=all_models
)

# "llama-3.1-8b-instant",
# "qwen/qwen3-32b",
# "openai/gpt-oss-20b",

groq_client = GroqClient(model_pool)


class ChatRequest(BaseModel):
    message: str

@app.get("/models/available")
def get_models():
    return groq_client.model_pool.get_available_models()

@app.post("/chat/auto")
def chat(request: ChatRequest):
    messages = [
        {"role": "user", "content": request.message}
    ]

    response = groq_client.chat(messages)

    return {
        "model_used": response["model"],
        "response": response["choices"][0]["message"]["content"],
    }


# @app.post("/chat/manual")
# def chat(request: ChatRequest):
#     messages = [
#         {"role": "user", "content": request.message}
#     ]

#     if request.model not in all_models:
#         return 401 invalid model

#     response = groq_client.chat(messages,model=model)

#     return {
#         "model_used": response["model"],
#         "response": response["choices"][0]["message"]["content"],
#     }


# @post(/models/reorder)
# def reorder_models():
#     # the usere should be able to set what model is his favorite that should be the first one that gets tried till its rate limited then it should go to the users second favorite and so on 