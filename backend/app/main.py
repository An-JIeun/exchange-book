from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import books, comments, dashboards, underlines, users

Base.metadata.create_all(bind=engine)

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
    return {"status": "ok"}
