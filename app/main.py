from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
import os

from app.database import init_db
from app.config import settings
from app.routers import patients, documents, chat

# Ensure directories exist
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path("data").mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Local Patient Records System",
    description="Voice-enabled, local-first patient records with AI assistance. Data stays local; only LLM calls go online.",
    version="1.0.0",
)

app.include_router(patients.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

# Static & templates
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "llm_model": settings.LLM_MODEL,
        },
    )

@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_model": settings.LLM_MODEL,
        "database": settings.DATABASE_URL,
    }
