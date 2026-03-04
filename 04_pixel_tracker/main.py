import os
import io
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, Response, Cookie
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import uvicorn

# ---------- Configuration ----------
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://username:password@host:5432/database"
)

# ---------- Database Setup ----------
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class PixelEvent(Base):
    __tablename__ = "pixel_tracker_events"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, index=True)
    user_agent = Column(String)
    ip_address = Column(String)
    referrer = Column(String)  # page embedding pixel
    original_url = Column(String)  # optional query param
    visitor_id = Column(String)  # cookie
    timestamp = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

# ---------- FastAPI App ----------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Utility ----------
def generate_transparent_pixel() -> io.BytesIO:
    """Generate a 1x1 transparent PNG"""
    image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def get_or_create_visitor_id(visitor_id: str | None) -> str:
    """Return existing visitor_id or generate a new UUID"""
    if visitor_id:
        return visitor_id
    return str(uuid.uuid4())


# ---------- Pixel Tracking Endpoint ----------
@app.get("/{slug:path}")
async def track_pixel(
    slug: str,
    request: Request,
    response: Response,
    visitor_id: str | None = Cookie(default=None),
):
    if not slug:
        slug = "/"

    # Extract data
    visitor_id = get_or_create_visitor_id(visitor_id)
    user_agent = request.headers.get("user-agent", "unknown")
    ip_address = request.client.host if request.client else "unknown"
    referrer = request.headers.get("referer", "unknown")
    original_url = request.query_params.get("url", None)

    # Save event to DB
    db = SessionLocal()
    try:
        event = PixelEvent(
            slug=slug,
            user_agent=user_agent,
            ip_address=ip_address,
            referrer=referrer,
            original_url=original_url,
            visitor_id=visitor_id,
        )
        db.add(event)
        db.commit()
    finally:
        db.close()

    # Set visitor_id cookie
    response.set_cookie(key="visitor_id", value=visitor_id, max_age=31536000)  # 1 year

    # Anti-caching headers
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    return StreamingResponse(
        generate_transparent_pixel(),
        media_type="image/png",
        headers=headers,
    )


# ---------- Run ----------
def main():
    uvicorn.run(app=app, port=8804)


if __name__ == "__main__":
    main()
