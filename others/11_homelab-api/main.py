import os
from fastapi import FastAPI, Depends
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Enum,
    JSON,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import datetime
from enum import Enum as PyEnum
from typing import List
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
import sys

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_SCHEMA = os.getenv("DB_SCHEMA","public")

required_vars = {
    "POSTGRES_HOST": DB_HOST,
    "POSTGRES_PORT": DB_PORT,
    "POSTGRES_DB": DB_NAME,
    "POSTGRES_USER": DB_USER,
    "POSTGRES_PASSWORD": DB_PASSWORD,
}

missing = [name for name, value in required_vars.items() if not value]

if missing:
    print(f"Missing required environment variables: {', '.join(missing)}")
    sys.exit(1)

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}" f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# -------------------------------------------------------------------
# Database
# -------------------------------------------------------------------

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------------
# Models
# -------------------------------------------------------------------


class Event(Base):
    __tablename__ = "events"
    __table_args__ = {"schema": DB_SCHEMA}


    id = Column(Integer, primary_key=True)
    text = Column(String, index=True, nullable=False)
    category = Column(String, index=True)
    event = Column(String, index=True)
    payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
# -------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------

from pydantic import BaseModel


class EventCreate(BaseModel):
    text: str
    category: str | None = None
    event: str | None = None
    payload: dict | None = None


class EventRead(EventCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# -------------------------------------------------------------------
# App
# -------------------------------------------------------------------

app = FastAPI(title="Homelab Events API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


@app.get("/", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Homelab Events API")


# -------------------------------------------------------------------
# Event API
# -------------------------------------------------------------------


@app.post("/events", response_model=EventRead)
def create_event(data: EventCreate, db: Session = Depends(get_db)):
    event = Event(**data.dict())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@app.get("/events", response_model=List[EventRead])
def list_events(
    category: str | None = None,
    event: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(Event)
    if category:
        q = q.filter(Event.category == category)
    if event:
        q = q.filter(Event.event == event)

    return q.order_by(Event.created_at.desc()).limit(limit).all()
