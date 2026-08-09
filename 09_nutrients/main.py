from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
    Date,
    DateTime,
    ForeignKey,
    Enum,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
import enum
import uvicorn
import os

# =========================================================
# DATABASE
# =========================================================
DATABASE_URL = os.getenv("DATABASE_URL","") #""

if DATABASE_URL == "":
    print("DATABASE_URL not defined, please create .env") 
    exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================================================
# ENUMS
# =========================================================
class HealthRating(str, enum.Enum):
    super_healthy = "super_healthy"
    good_healthy = "good_healthy"
    ok_healthy = "ok_healthy"
    slightly_unhealthy = "slightly_unhealthy"
    unhealthy = "unhealthy"
    very_unhealthy = "very_unhealthy"


# =========================================================
# DATABASE MODELS
# =========================================================
class Food(Base):
    __tablename__ = "foods"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    calories_per_100g = Column(Float, nullable=False)
    protein_per_100g = Column(Float, nullable=False)
    icon_emoji = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    logs = relationship("FoodLog", back_populates="food")


class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    id = Column(Integer, primary_key=True, index=True)
    health_rating = Column(Enum(HealthRating), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    food_logs = relationship(
        "FoodLog", back_populates="diary_entry", cascade="all, delete-orphan"
    )


class FoodLog(Base):
    __tablename__ = "food_logs"
    id = Column(Integer, primary_key=True, index=True)
    diary_entry_id = Column(
        Integer, ForeignKey("diary_entries.id", ondelete="CASCADE"), nullable=False
    )
    food_id = Column(Integer, ForeignKey("foods.id"), nullable=False)
    grams_eaten = Column(Float, nullable=False)
    eaten_day = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    diary_entry = relationship("DiaryEntry", back_populates="food_logs")
    food = relationship("Food", back_populates="logs")


# =========================================================
# PYDANTIC SCHEMAS
# =========================================================
# ---------------- FOOD ----------------
class FoodCreate(BaseModel):
    name: str
    calories_per_100g: float
    protein_per_100g: float
    icon_emoji: Optional[str] = None


class FoodUpdate(BaseModel):
    name: Optional[str] = None
    calories_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    icon_emoji: Optional[str] = None


class FoodResponse(BaseModel):
    id: int
    name: str
    calories_per_100g: float
    protein_per_100g: float
    icon_emoji: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------- FOOD LOG ----------------
class FoodLogCreate(BaseModel):
    food_id: int
    grams_eaten: float
    eaten_day: date


class FoodLogUpdate(BaseModel):
    grams_eaten: Optional[float] = None
    eaten_day: Optional[date] = None
    food_id: Optional[int] = None


class FoodLogResponse(BaseModel):
    id: int
    diary_entry_id: int
    food_id: int
    grams_eaten: float
    eaten_day: date
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------- DIARY ----------------
class DiaryCreate(BaseModel):
    health_rating: HealthRating
    notes: Optional[str] = None


class DiaryUpdate(BaseModel):
    health_rating: Optional[HealthRating] = None
    notes: Optional[str] = None


class DiaryResponse(BaseModel):
    id: int
    health_rating: HealthRating
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    food_logs: List[FoodLogResponse] = []

    class Config:
        from_attributes = True


# =========================================================
# FASTAPI APP
# =========================================================
app = FastAPI(title="Food Diary API", version="1.0.0")
Base.metadata.create_all(bind=engine)


# =========================================================
# ROOT
# =========================================================
@app.get("/")
def root():
    return {"message": "Food Diary API running"}


# =========================================================
# FOOD ENDPOINTS
# =========================================================
@app.post("/foods", response_model=FoodResponse)
def create_food(food: FoodCreate, db: Session = Depends(get_db)):
    existing = db.query(Food).filter(Food.name == food.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Food already exists")
    db_food = Food(**food.model_dump())
    db.add(db_food)
    db.commit()
    db.refresh(db_food)
    return db_food


@app.get("/foods", response_model=List[FoodResponse])
def get_foods(db: Session = Depends(get_db)):
    return db.query(Food).all()


@app.get("/foods/{food_id}", response_model=FoodResponse)
def get_food(food_id: int, db: Session = Depends(get_db)):
    food = db.query(Food).filter(Food.id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    return food


@app.put("/foods/{food_id}", response_model=FoodResponse)
def update_food(food_id: int, update_data: FoodUpdate, db: Session = Depends(get_db)):
    food = db.query(Food).filter(Food.id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    updates = update_data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(food, key, value)
    db.commit()
    db.refresh(food)
    return food


@app.delete("/foods/{food_id}")
def delete_food(food_id: int, db: Session = Depends(get_db)):
    food = db.query(Food).filter(Food.id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    db.delete(food)
    db.commit()
    return {"message": "Food deleted"}


@app.get("/foods/search/{query}", response_model=List[FoodResponse])
def search_foods(query: str, db: Session = Depends(get_db)):
    return db.query(Food).filter(Food.name.ilike(f"%{query}%")).all()


# =========================================================
# DIARY ENDPOINTS
# =========================================================
@app.post("/diary", response_model=DiaryResponse)
def create_diary_entry(diary: DiaryCreate, db: Session = Depends(get_db)):
    db_diary = DiaryEntry(**diary.model_dump())
    db.add(db_diary)
    db.commit()
    db.refresh(db_diary)
    return db_diary


@app.get("/diary", response_model=List[DiaryResponse])
def get_diary_entries(db: Session = Depends(get_db)):
    return db.query(DiaryEntry).all()


@app.get("/diary/{diary_id}", response_model=DiaryResponse)
def get_diary_entry(diary_id: int, db: Session = Depends(get_db)):
    diary = db.query(DiaryEntry).filter(DiaryEntry.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="Diary entry not found")
    return diary


@app.put("/diary/{diary_id}", response_model=DiaryResponse)
def update_diary_entry(
    diary_id: int, update_data: DiaryUpdate, db: Session = Depends(get_db)
):
    diary = db.query(DiaryEntry).filter(DiaryEntry.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="Diary entry not found")
    updates = update_data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(diary, key, value)
    db.commit()
    db.refresh(diary)
    return diary


@app.delete("/diary/{diary_id}")
def delete_diary_entry(diary_id: int, db: Session = Depends(get_db)):
    diary = db.query(DiaryEntry).filter(DiaryEntry.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="Diary entry not found")
    db.delete(diary)
    db.commit()
    return {"message": "Diary entry deleted"}


# =========================================================
# FOOD LOG ENDPOINTS
# =========================================================
@app.post("/diary/{diary_id}/foods", response_model=FoodLogResponse)
def add_food_to_diary(
    diary_id: int, food_log: FoodLogCreate, db: Session = Depends(get_db)
):
    diary = db.query(DiaryEntry).filter(DiaryEntry.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="Diary entry not found")
    food = db.query(Food).filter(Food.id == food_log.food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    db_food_log = FoodLog(diary_entry_id=diary_id, **food_log.model_dump())
    db.add(db_food_log)
    db.commit()
    db.refresh(db_food_log)
    return db_food_log


@app.get("/food-logs/day/{eaten_day}", response_model=List[FoodLogResponse])
def get_food_logs_for_day(eaten_day: date, db: Session = Depends(get_db)):
    return db.query(FoodLog).filter(FoodLog.eaten_day == eaten_day).all()


@app.put("/food-logs/{food_log_id}", response_model=FoodLogResponse)
def update_food_log(
    food_log_id: int, update_data: FoodLogUpdate, db: Session = Depends(get_db)
):
    log = db.query(FoodLog).filter(FoodLog.id == food_log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Food log not found")
    updates = update_data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(log, key, value)
    db.commit()
    db.refresh(log)
    return log


@app.delete("/food-logs/{food_log_id}")
def delete_food_log(food_log_id: int, db: Session = Depends(get_db)):
    log = db.query(FoodLog).filter(FoodLog.id == food_log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Food log not found")
    db.delete(log)
    db.commit()
    return {"message": "Food log deleted"}


# =========================================================
# STATS ENDPOINTS
# =========================================================
@app.get("/stats/day/{eaten_day}")
def get_day_stats(eaten_day: date, db: Session = Depends(get_db)):
    logs = db.query(FoodLog).filter(FoodLog.eaten_day == eaten_day).all()
    total_calories = 0
    total_protein = 0
    foods = []
    for log in logs:
        food = log.food
        calories = (food.calories_per_100g / 100) * log.grams_eaten
        protein = (food.protein_per_100g / 100) * log.grams_eaten
        total_calories += calories
        total_protein += protein
        foods.append(
            {
                "food_name": food.name,
                "grams_eaten": log.grams_eaten,
                "calories": round(calories, 2),
                "protein": round(protein, 2),
                "emoji": food.icon_emoji,
            }
        )
    return {
        "date": eaten_day,
        "total_calories": round(total_calories, 2),
        "total_protein": round(total_protein, 2),
        "foods": foods,
    }


# =========================================================
# RUN:
# uvicorn main:app --reload
# =========================================================

if __name__ == "__main__":
    uvicorn.run(app)