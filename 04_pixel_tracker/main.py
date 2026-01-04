import os
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import io


POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "pixeldb")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

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

# FastAPI app
app = FastAPI()

# 1x1 transparent PNG
PIXEL_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\xdac```\x00\x00\x00\x05\x00\x01"
    b"\x0d\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

@app.get("/{slug:path}")
async def track_pixel(slug: str, request: Request):
    db = SessionLocal()

    if len(slug) == 0:
        slug = "/"
    try:
        event = PixelEvent(
            slug=slug,
            user_agent=request.headers.get("user-agent", "unknown"),
            ip_address=request.client.host
        )
        db.add(event)
        db.commit()
    finally:
        db.close()

    return StreamingResponse(io.BytesIO(PIXEL_BYTES), media_type="image/png")
