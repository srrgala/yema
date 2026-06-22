"""
FastAPI application — punto de entrada de la API y servidor de estáticos.

Arranque local:
    uvicorn api:app --reload

Producción (Render):
    uvicorn api:app --host 0.0.0.0 --port $PORT
"""

import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from main import process_input

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

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
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_ALLOWED_ORIGINS = [
    "https://brief-generator-5z0a.onrender.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────


class AnswerItem(BaseModel):
    question: str = Field(..., max_length=500, description="Pregunta formulada por el sistema")
    answer: str = Field(..., max_length=1000, description="Respuesta del usuario")


class ProcessRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Texto libre del cliente")
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
@limiter.limit("10/minute")
async def process(request: Request, body: ProcessRequest):
    """
    Punto de entrada principal del generador.

    - **Primera llamada**: envía solo `text`.
    - **Segunda llamada**: envía `text` + `answers` con las respuestas a las preguntas.
    """
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=422, detail="El campo 'text' no puede estar vacío.")

    answers_dicts = (
        [item.model_dump() for item in body.answers] if body.answers else []
    )

    result = await process_input(text=body.text.strip(), answers=answers_dicts)
    return result


# ── Static files (must be mounted last) ──────────────────────────────────────

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
