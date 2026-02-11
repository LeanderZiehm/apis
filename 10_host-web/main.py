import os
import hashlib
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import (
    create_engine,
    String,
    Text,
    DateTime,
    Integer,
    select,
    desc,
    Index,
    ForeignKey,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
    Session,
    relationship,
)
from sqlalchemy.exc import IntegrityError
import uvicorn


# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pages.db")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------

class Page(Base):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    slug: Mapped[Optional[str]] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    html_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    view_events: Mapped[list["PageView"]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan"
    )


class PageView(Base):
    __tablename__ = "page_views"

    id: Mapped[int] = mapped_column(primary_key=True)

    page_id: Mapped[int] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"),
        index=True
    )

    page: Mapped["Page"] = relationship(back_populates="view_events")

    viewed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )

    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    referer: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("ix_page_views_page_time", "page_id", "viewed_at"),
    )


Base.metadata.create_all(bind=engine)


# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def resolve_page(identifier: str, db: Session) -> Optional[Page]:
    return db.scalar(
        select(Page).where(
            (Page.hash == identifier) | (Page.slug == identifier)
        )
    )


# -----------------------------------------------------------------------------
# Create Page
# -----------------------------------------------------------------------------

@app.post("/submit")
def create_page(
    html_content: str = Form(...),
    slug: Optional[str] = Form(None),
    db: Session = Depends(get_db)
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
        raise HTTPException(status_code=400, detail="Slug already exists.")

    return RedirectResponse(
        url=f"/p/{page.slug or page.hash}",
        status_code=303,
    )


# -----------------------------------------------------------------------------
# Update Slug (AJAX)
# -----------------------------------------------------------------------------

@app.post("/api/pages/{identifier}/slug")
def update_slug(
    identifier: str,
    slug: str = Form(...),
    db: Session = Depends(get_db),
):
    page = resolve_page(identifier, db)
    if not page:
        raise HTTPException(status_code=404)

    page.slug = slug

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            status_code=400,
            content={"error": "Slug already taken"}
        )

    return {"success": True, "slug": slug}


# -----------------------------------------------------------------------------
# Homepage
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def homepage(db: Session = Depends(get_db)):

    results = db.execute(
        select(
            Page,
            func.count(PageView.id).label("view_count")
        )
        .outerjoin(PageView)
        .group_by(Page.id)
        .order_by(desc("view_count"))
    ).all()

    items = ""
    for page, view_count in results:
        identifier = page.slug or page.hash
        items += f"""
        <li>
            <div>
                <a href="/p/{identifier}">{identifier}</a>
                <small> · views: {view_count}</small>
            </div>
            <button class="edit-btn" onclick="openModal('{page.hash}')">Edit</button>
        </li>
        """

    return f"""
    <html>
    <head>
        {styles()}
    </head>
    <body>

    <div class="card">
        <h2>Create Page</h2>
        <form action="/submit" method="post">
            <input type="text" name="slug" placeholder="Optional slug">
            <textarea name="html_content" rows="8" required></textarea>
            <button type="submit">Save</button>
        </form>
    </div>

    <h2>Pages</h2>
    <ul>{items}</ul>

    {modal()}

    </body>
    </html>
    """


# -----------------------------------------------------------------------------
# View Page
# -----------------------------------------------------------------------------

@app.get("/p/{identifier}", response_class=HTMLResponse)
def view_page(
    identifier: str,
    request: Request,
    db: Session = Depends(get_db)
):
    page = resolve_page(identifier, db)
    if not page:
        raise HTTPException(status_code=404)

    # Record analytics event
    view = PageView(
        page_id=page.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer"),
    )
    db.add(view)
    db.commit()

    view_count = db.scalar(
        select(func.count(PageView.id)).where(PageView.page_id == page.id)
    )

    return f"""
    <html>
    <head>
        {styles()}
    </head>
    <body>

    <div style="display:flex;justify-content:space-between;margin-bottom:20px;">
        <a href="/">← Back</a>
        <div>
            <span>Views: {view_count}</span>
            <button class="edit-btn" onclick="openModal('{page.hash}')">
                Edit Slug
            </button>
        </div>
    </div>

    {page.html_content}

    {modal()}

    </body>
    </html>
    """


# -----------------------------------------------------------------------------
# UI Helpers
# -----------------------------------------------------------------------------

def styles():
    return """
    <style>
        body {
            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
            margin:0;
            padding:40px;
            background:#f5f7fa;
        }

        .card {
            background:white;
            padding:25px;
            border-radius:14px;
            box-shadow:0 8px 25px rgba(0,0,0,0.05);
            margin-bottom:30px;
        }

        input, textarea {
            width:100%;
            padding:12px;
            border-radius:8px;
            border:1px solid #ddd;
            margin-bottom:15px;
        }

        button {
            background:#111;
            color:white;
            border:none;
            padding:8px 14px;
            border-radius:8px;
            cursor:pointer;
        }

        .edit-btn {
            background:#eee;
            color:#111;
        }

        ul { list-style:none; padding:0; }

        li {
            background:white;
            padding:15px;
            border-radius:10px;
            margin-bottom:10px;
            display:flex;
            justify-content:space-between;
        }

        .modal {
            display:none;
            position:fixed;
            inset:0;
            background:rgba(0,0,0,0.4);
            justify-content:center;
            align-items:center;
        }

        .modal-content {
            background:white;
            padding:25px;
            border-radius:12px;
            width:400px;
        }

        .error { border:2px solid #e53935 !important; }
        .success { border:2px solid #2e7d32 !important; }

        .error-text {
            color:#e53935;
            font-size:13px;
        }
    </style>
    """


def modal():
    return """
    <div id="modal" class="modal">
        <div class="modal-content">
            <h3>Edit Slug</h3>
            <input type="text" id="slugInput">
            <div id="errorText" class="error-text"></div>
            <br>
            <button onclick="saveSlug()">Save</button>
            <button onclick="closeModal()">Cancel</button>
        </div>
    </div>

    <script>
        let currentId = null;

        function openModal(id) {
            currentId = id;
            document.getElementById('modal').style.display = 'flex';
            document.getElementById('slugInput').value = '';
            document.getElementById('slugInput').classList.remove('error','success');
            document.getElementById('errorText').innerText = '';
        }

        function closeModal() {
            document.getElementById('modal').style.display = 'none';
        }

        async function saveSlug() {
            const input = document.getElementById('slugInput');
            const slug = input.value;

            const formData = new FormData();
            formData.append("slug", slug);

            const res = await fetch(`/api/pages/${currentId}/slug`, {
                method: "POST",
                body: formData
            });

            if (!res.ok) {
                input.classList.add("error");
                document.getElementById('errorText').innerText = "Slug already taken";
            } else {
                input.classList.remove("error");
                input.classList.add("success");
                setTimeout(() => location.reload(), 600);
            }
        }
    </script>
    """


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, port=8010)
