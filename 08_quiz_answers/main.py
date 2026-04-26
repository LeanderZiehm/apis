from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from dotenv import load_dotenv
from fastapi.openapi.docs import get_swagger_ui_html

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env")


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# -------------------------
# MODELS
# -------------------------


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True)
    question_id = Column(String)
    username = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    question_id = Column(String)
    username = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)

# -------------------------
# APP SETUP
# -------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="OCR API Docs")


# -------------------------
# HELPERS
# -------------------------


def db():
    return SessionLocal()


# -------------------------
# ANSWERS API
# -------------------------


@app.get("/answers/{question_id}")
def get_answers(question_id: str):
    session = db()
    results = (
        session.query(Answer)
        .filter(Answer.question_id == question_id)
        .order_by(Answer.created_at.desc())
        .all()
    )

    return [
        {"username": r.username, "content": r.content, "created_at": r.created_at}
        for r in results
    ]


@app.post("/answers")
def post_answer(payload: dict):
    session = db()

    answer = Answer(
        question_id=payload["question_id"],
        username=payload["username"],
        content=payload["content"],
        created_at=datetime.utcnow(),
    )

    session.add(answer)
    session.commit()

    return {"status": "ok"}


# -------------------------
# COMMENTS API
# -------------------------


@app.get("/comments/{question_id}")
def get_comments(question_id: str):
    session = db()

    results = (
        session.query(Comment)
        .filter(Comment.question_id == question_id)
        .order_by(Comment.created_at.asc())
        .all()
    )

    return [
        {"username": r.username, "content": r.content, "created_at": r.created_at}
        for r in results
    ]


@app.post("/comments")
def post_comment(payload: dict):
    session = db()

    comment = Comment(
        question_id=payload["question_id"],
        username=payload["username"],
        content=payload["content"],
        created_at=datetime.utcnow(),
    )

    session.add(comment)
    session.commit()

    return {"status": "ok"}
