import os
import io
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image


POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "pixeldb")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Database setup
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class PixelEvent(Base):
    __tablename__ = "pixel_tracker_events"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, index=True)
    user_agent = Column(String)
    ip_address = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def generate_transparent_pixel() -> io.BytesIO:
    """
    Generate a 1x1 transparent PNG using Pillow.
    """
    image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


@app.get("/{slug:path}")
async def track_pixel(slug: str, request: Request):
    if not slug:
        slug = "/"

    db = SessionLocal()
    try:
        event = PixelEvent(
            slug=slug,
            user_agent=request.headers.get("user-agent", "unknown"),
            ip_address=request.client.host if request.client else "unknown",
        )
        db.add(event)
        db.commit()
    finally:
        db.close()

    headers = {
        # Strong anti-caching guarantees
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    return StreamingResponse(
        generate_transparent_pixel(),
        media_type="image/png",
        headers=headers,
    )
