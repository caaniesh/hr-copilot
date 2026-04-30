from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routes import analysis, assistant, decision, export, interview, resume, system
from app.utils.config import settings


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Production-ready HR copilot for resume analysis and assisted technical interviews.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")

app.include_router(system.router)
app.include_router(resume.router)
app.include_router(analysis.router)
app.include_router(assistant.router)
app.include_router(interview.router)
app.include_router(export.router)
app.include_router(decision.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(settings.static_dir / "index.html")
