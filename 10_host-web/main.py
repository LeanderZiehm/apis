import os
import hashlib
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import (
    create_engine,
    String,
    Text,
    DateTime,
    Integer,
    select,
    desc,
    func,
    Index,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
    Session,
)
from sqlalchemy.exc import IntegrityError
import uvicorn


# -----------------------------------------------------------------------------
# Database configuration
# -----------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# -----------------------------------------------------------------------------
# ORM Model
# -----------------------------------------------------------------------------

class Page(Base):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    slug: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True, nullable=True)
    html_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    views: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_pages_created_at", "created_at"),
        Index("ix_pages_views", "views"),
    )


Base.metadata.create_all(bind=engine)


# -----------------------------------------------------------------------------
# Pydantic Schemas
# -----------------------------------------------------------------------------

class PageCreate(BaseModel):
    html_content: str = Field(..., description="Raw HTML content to store")
    slug: Optional[str] = Field(None, description="Optional custom URL slug")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "html_content": "<html><body><h1>Hello</h1></body></html>",
                "slug": "my-custom-page"
            }
        }
    )


class PageResponse(BaseModel):
    hash: str
    slug: Optional[str]
    created_at: datetime
    views: int

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------

app = FastAPI(
    title="HTML Page Store",
    description="Store and serve raw HTML pages with hash or custom slug URLs.",
    version="1.0.0",
)


# -----------------------------------------------------------------------------
# Dependency
# -----------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------------------------------------------------------
# Utility
# -----------------------------------------------------------------------------

def generate_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def inject_navigation(html: str) -> str:
    nav = """
    <div style="
        position:fixed;
        top:0;
        left:0;
        width:100%;
        background:#111;
        color:white;
        padding:10px;
        z-index:9999;
        font-family:sans-serif;">
        <a href="/" style="color:white;text-decoration:none;">⬅ Back</a>
    </div>
    <div style="margin-top:50px;"></div>
    """
    return nav + html


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.post("/api/pages", response_model=PageResponse, status_code=201)
def create_page(payload: PageCreate, db: Session = Depends(get_db)):
    page_hash = generate_hash(payload.html_content)

    page = Page(
        hash=page_hash,
        slug=payload.slug,
        html_content=payload.html_content,
    )

    db.add(page)
    try:
        db.commit()
        db.refresh(page)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Hash or slug already exists.")

    return page


@app.get("/api/pages", response_model=List[PageResponse])
def list_pages(db: Session = Depends(get_db)):
    pages = db.scalars(select(Page)).all()
    return pages


# -----------------------------------------------------------------------------
# Web UI
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def homepage(db: Session = Depends(get_db)):
    recent = db.scalars(
        select(Page).order_by(desc(Page.created_at)).limit(10)
    ).all()

    most_visited = db.scalars(
        select(Page).order_by(desc(Page.views)).limit(10)
    ).all()

    def render_list(pages):
        items = ""
        for p in pages:
            url = f"/p/{p.slug or p.hash}"
            items += f"""
            <li>
                <a href="{url}">{p.slug or p.hash}</a>
                <small>({p.created_at.strftime('%Y-%m-%d %H:%M:%S')}, views: {p.views})</small>
            </li>
            """
        return f"<ul>{items}</ul>"

    return f"""
    <html>
    <head>
        <title>HTML Store</title>
    </head>
    <body style="font-family:sans-serif;">
        <h1>Add HTML Page</h1>
        <form action="/submit" method="post">
            <input type="text" name="slug" placeholder="Optional custom slug" style="width:100%;padding:8px;"><br><br>
            <textarea name="html_content" rows="15" style="width:100%;padding:8px;"></textarea><br><br>
            <button type="submit" style="padding:10px 20px;">Save</button>
        </form>

        <hr>

        <h2>Most Recent</h2>
        {render_list(recent)}

        <h2>Most Visited</h2>
        {render_list(most_visited)}

    </body>
    </html>
    """


@app.post("/submit")
def submit_form(
    html_content: str = Form(...),
    slug: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    page_hash = generate_hash(html_content)

    page = Page(
        hash=page_hash,
        slug=slug or None,
        html_content=html_content,
    )

    db.add(page)
    try:
        db.commit()
        db.refresh(page)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Hash or slug already exists.")

    return RedirectResponse(
        url=f"/p/{page.slug or page.hash}",
        status_code=303,
    )


@app.get("/p/{identifier}", response_class=HTMLResponse)
def view_page(identifier: str, db: Session = Depends(get_db)):
    page = db.scalar(
        select(Page).where(
            (Page.hash == identifier) | (Page.slug == identifier)
        )
    )

    if not page:
        raise HTTPException(status_code=404, detail="Page not found.")

    page.views += 1
    db.commit()

    return inject_navigation(page.html_content)


if __name__ == "__main__":
    uvicorn.run(app=app,port=8010)