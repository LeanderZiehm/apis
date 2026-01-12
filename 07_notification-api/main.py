import os

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

if not CHAT_ID:
    raise RuntimeError("TELEGRAM_CHAT_ID is not set")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

app = FastAPI()


class MessageIn(BaseModel):
    text: str


@app.post("/notify/me")
def send_message(payload: MessageIn):
    response = requests.post(
        TELEGRAM_URL,
        json={
            "chat_id": CHAT_ID,
            "text": payload.text,
        },
        timeout=10,
    )

    if not response.ok:
        raise HTTPException(
            status_code=500,
            detail=response.text,
        )

    return {"ok": True}
