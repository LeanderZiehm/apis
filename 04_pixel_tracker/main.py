import os
import io
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, Cookie
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from PIL import Image
import uvicorn

# ============================================================
# Configuration
# ============================================================
DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    print("DATABASE_URL not defined, please create/set your environment variable.")
    raise SystemExit(1)
# ============================================================
# Database Setup
# ============================================================
Base = declarative_base()
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class PixelEvent(Base):
    __tablename__ = "pixel_tracker_events_v2"
    id = Column(Integer, primary_key=True, index=True)
    # Requested pixel path / slug
    slug = Column(String, index=True, nullable=True)
    # Client IP address
    ip_address = Column(String, nullable=True)
    # First-party visitor cookie
    visitor_id = Column(String, index=True, nullable=True)
    # Browser information
    user_agent = Column(Text, nullable=True)
    # Time of request
    timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    # Full request URL, including query string
    raw_request_url = Column(Text, nullable=False)
    # Raw query-string portion only
    query_parameters = Column(Text, nullable=True)
    # Optional URL supplied as ?url=...
    source_url = Column(Text, nullable=True)
    # Page embedding the pixel
    referrer = Column(Text, nullable=True)

# Creates the table if it doesn't already exist.
# For production schema management, Alembic migrations are preferable.
Base.metadata.create_all(bind=engine)
# ============================================================
# FastAPI App
# ============================================================
app = FastAPI()


# ============================================================
# Utility Functions
# ============================================================
def generate_transparent_pixel() -> io.BytesIO:
    """Generate a 1x1 transparent PNG."""
    image = Image.new(
        "RGBA",
        (1, 1),
        (0, 0, 0, 0),
    )
    buffer = io.BytesIO()
    image.save(
        buffer,
        format="PNG",
    )
    buffer.seek(0)
    return buffer


def get_or_create_visitor_id(visitor_id: str | None) -> str:
    """Return existing visitor_id or generate a new UUID."""
    if visitor_id:
        return visitor_id
    return str(uuid.uuid4())


def get_raw_request_url(request: Request) -> str:
    """
    Return the full request URL.
    Example:
    https://tracker.example.com/foo/bar?url=https%3A%2F%2Fexample.com%2Fpage&utm_source=test
    """
    return str(request.url)


def get_raw_query_parameters(request: Request) -> str | None:
    """
    Return only the raw query-string portion.
    Example:
    url=https%3A%2F%2Fexample.com%2Fpage&utm_source=test
    This intentionally preserves the encoded query string instead of
    converting it into a Python dictionary.
    """
    query_string = request.scope.get("query_string", b"")
    if not query_string:
        return None
    return query_string.decode(
        "latin-1",
        errors="replace",
    )


# ============================================================
# Pixel Tracking Endpoint
# ============================================================
@app.get("/{slug:path}")
async def track_pixel(
    slug: str,
    request: Request,
    visitor_id: str | None = Cookie(default=None),
):
    if not slug:
        slug = "/"
    # --------------------------------------------------------
    # Extract request information
    # --------------------------------------------------------
    visitor_id = get_or_create_visitor_id(visitor_id)
    user_agent = request.headers.get(
        "user-agent",
        None,
    )
    ip_address = request.client.host if request.client else "unknown"
    referrer = request.headers.get(
        "referer",
        None,
    )
    source_url = request.query_params.get(
        "url",
        None,
    )
    # Full URL including query string
    raw_request_url = get_raw_request_url(request)
    # Raw query string only
    query_parameters = get_raw_query_parameters(request)
    # --------------------------------------------------------
    # Save event
    # --------------------------------------------------------
    db = SessionLocal()
    try:
        event = PixelEvent(
            slug=slug,
            user_agent=user_agent,
            ip_address=ip_address,
            referrer=referrer,
            source_url=source_url,
            visitor_id=visitor_id,
            raw_request_url=raw_request_url,
            query_parameters=query_parameters,
        )
        db.add(event)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    # --------------------------------------------------------
    # Generate response
    # --------------------------------------------------------
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    response = StreamingResponse(
        generate_transparent_pixel(),
        media_type="image/png",
        headers=headers,
    )
    # Set cookie on the actual response being returned.
    response.set_cookie(
        key="visitor_id",
        value=visitor_id,
        max_age=31536000,  # 1 year
        httponly=True,
        samesite="lax",
    )
    return response


# ============================================================
# Run
# ============================================================
def main():
    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=8804,
    )


if __name__ == "__main__":
    main()
