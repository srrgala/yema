"""
FastAPI application — punto de entrada de la API y servidor de estáticos.

Arranque local:
    uvicorn api:app --reload

Producción (Render):
    uvicorn api:app --host 0.0.0.0 --port $PORT
"""

import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from main import process_input

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Brief Generator",
    description="Convierte textos desordenados de clientes en briefs de branding estructurados.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# CORS — restrictivo por defecto; ampliar en producción si se necesita
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────


class AnswerItem(BaseModel):
    question: str = Field(..., description="Pregunta formulada por el sistema")
    answer: str = Field(..., description="Respuesta del usuario")


class ProcessRequest(BaseModel):
    text: str = Field(..., description="Texto libre del cliente")
    answers: list[AnswerItem] | None = Field(
        default=None,
        description="Respuestas a las preguntas de clarificación (segunda llamada)",
    )


class ProcessResponse(BaseModel):
    status: str
    message: str | None = None
    questions: list[str] | None = None
    brief: dict | None = None


# ── Endpoints de API ──────────────────────────────────────────────────────────


@app.get("/api/health", tags=["Sistema"])
@app.head("/api/health", include_in_schema=False)
async def health():
    """Comprueba que el servicio está activo."""
    return {"status": "ok", "service": "brief-generator"}


@app.post("/api/process", response_model=ProcessResponse, tags=["Brief"])
async def process(request: ProcessRequest):
    """
    Punto de entrada principal del generador.

    - **Primera llamada**: envía solo `text`.
    - **Segunda llamada**: envía `text` + `answers` con las respuestas a las preguntas.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=422, detail="El campo 'text' no puede estar vacío.")

    answers_dicts = (
        [item.model_dump() for item in request.answers] if request.answers else []
    )

    result = await process_input(text=request.text.strip(), answers=answers_dicts)
    return result


# ── Static files (must be mounted last) ──────────────────────────────────────

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
