from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .config import settings
from .database import Base, engine
from .routers import books, comments, dashboards, underlines, users

Base.metadata.create_all(bind=engine)


def _ensure_user_password_column():
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = [column["name"] for column in inspector.get_columns("users")]
    if "password_hash" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(128) NULL"))


_ensure_user_password_column()


def _ensure_user_admin_column():
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = [column["name"] for column in inspector.get_columns("users")]
    if "is_admin" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))


_ensure_user_admin_column()


def _ensure_user_reading_status_column():
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = [column["name"] for column in inspector.get_columns("users")]
    if "reading_status" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN reading_status VARCHAR(20) NOT NULL DEFAULT 'before'")
        )


_ensure_user_reading_status_column()


def _ensure_book_total_pages_column():
    inspector = inspect(engine)
    if "books" not in inspector.get_table_names():
        return

    columns = [column["name"] for column in inspector.get_columns("books")]
    if "total_pages" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE books ADD COLUMN total_pages INT NULL"))


_ensure_book_total_pages_column()


def _ensure_nullable_reference_columns():
    inspector = inspect(engine)
    if "underlines" in inspector.get_table_names():
        underline_columns = {
            column["name"]: column for column in inspector.get_columns("underlines")
        }
        book_id_column = underline_columns.get("book_id")
        if book_id_column and not book_id_column.get("nullable", True):
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE underlines MODIFY COLUMN book_id INT NULL"))

    if "comments" in inspector.get_table_names():
        comment_columns = {
            column["name"]: column for column in inspector.get_columns("comments")
        }
        underline_id_column = comment_columns.get("underline_id")
        if underline_id_column and not underline_id_column.get("nullable", True):
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE comments MODIFY COLUMN underline_id INT NULL"))


_ensure_nullable_reference_columns()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api")
app.include_router(books.router, prefix="/api")
app.include_router(underlines.router, prefix="/api")
app.include_router(comments.router, prefix="/api")
app.include_router(dashboards.router, prefix="/api")


@app.get("/api/health")
def health_check():
    """
    Health check endpoint for UptimeRobot.
    This endpoint is pinged every 5 minutes to keep the app awake on Render's free tier.
    """
    return {"status": "ok"}


@app.head("/api/health")
def health_check_head():
    return


@app.get("/healthz")
def healthz_check():
    return {"status": "ok"}


@app.head("/healthz")
def healthz_check_head():
    return
