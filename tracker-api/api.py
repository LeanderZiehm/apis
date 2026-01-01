from fastapi import FastAPI, Depends
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Enum,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import datetime
from enum import Enum as PyEnum
from typing import List
from fastapi.openapi.docs import get_swagger_ui_html

# -------------------------------------------------------------------
# Database
# -------------------------------------------------------------------

DATABASE_URL = "sqlite:///./data.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
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

    id = Column(Integer, primary_key=True)
    category = Column(String, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TimerAction(str, PyEnum):
    START = "START"
    END = "END"


class TimerEvent(Base):
    __tablename__ = "timer_events"

    id = Column(Integer, primary_key=True)
    category = Column(String, index=True)
    name = Column(String, index=True)
    action = Column(Enum(TimerAction), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True)
    category = Column(String, index=True)
    name = Column(String, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# -------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------

from pydantic import BaseModel

class EventCreate(BaseModel):
    category: str
    name: str


class EventRead(EventCreate):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class TimerCreate(BaseModel):
    category: str
    name: str
    action: TimerAction


class TimerRead(TimerCreate):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class MeasurementCreate(BaseModel):
    category: str
    name: str
    value: float
    unit: str


class MeasurementRead(MeasurementCreate):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# -------------------------------------------------------------------
# App
# -------------------------------------------------------------------

app = FastAPI(title="Minimal Event / Timer / Measurement API")

Base.metadata.create_all(bind=engine)

@app.get("/", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="OCR API Docs")



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
    name: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Event)

    if category:
        query = query.filter(Event.category == category)
    if name:
        query = query.filter(Event.name == name)

    return query.order_by(Event.created_at.desc()).limit(limit).all()

# -------------------------------------------------------------------
# Timer API
# -------------------------------------------------------------------

@app.post("/timers", response_model=TimerRead)
def create_timer_event(data: TimerCreate, db: Session = Depends(get_db)):
    timer_event = TimerEvent(
        category=data.category,
        name=data.name,
        action=data.action,
    )
    db.add(timer_event)
    db.commit()
    db.refresh(timer_event)
    return timer_event


@app.get("/timers", response_model=List[TimerRead])
def list_timer_events(
    category: str | None = None,
    name: str | None = None,
    action: TimerAction | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(TimerEvent)

    if category:
        query = query.filter(TimerEvent.category == category)
    if name:
        query = query.filter(TimerEvent.name == name)
    if action:
        query = query.filter(TimerEvent.action == action)

    return query.order_by(TimerEvent.created_at.desc()).limit(limit).all()

# -------------------------------------------------------------------
# Measurement API
# -------------------------------------------------------------------

@app.post("/measurements", response_model=MeasurementRead)
def create_measurement(data: MeasurementCreate, db: Session = Depends(get_db)):
    measurement = Measurement(**data.dict())
    db.add(measurement)
    db.commit()
    db.refresh(measurement)
    return measurement


@app.get("/measurements", response_model=List[MeasurementRead])
def list_measurements(
    category: str | None = None,
    name: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Measurement)

    if category:
        query = query.filter(Measurement.category == category)
    if name:
        query = query.filter(Measurement.name == name)

    return query.order_by(Measurement.created_at.desc()).limit(limit).all()
