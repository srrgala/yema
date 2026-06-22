"""
Orquestador de las tres fases del generador de briefs.
Diseño stateless: el cliente concatena el contexto entre llamadas.
"""

import json
import logging

import anthropic

from core.classifier import classify_input, is_identity_question
from core.identity import get_identity_response
from core.extractor import extract_fields, get_missing_critical_fields
from core.clarifier import generate_questions
from core.generator import generate_brief

logger = logging.getLogger(__name__)


async def process_input(text: str, answers: list[dict] | None = None) -> dict:
    """
    Punto de entrada principal. Ejecuta el flujo de tres fases.

    Args:
        text:    Texto libre del cliente (obligatorio en todas las llamadas).
        answers: Lista de {question, answer} de la ronda de clarificación.
                 Si se proporciona, se salta directamente a la Fase 3.

    Returns:
        Dict con la clave "status" y datos adicionales según la fase:
        - {"status": "invalid",            "message": str}
        - {"status": "identity",           "message": str}
        - {"status": "needs_clarification","questions": list[str]}
        - {"status": "ready",              "brief": dict}
        - {"status": "error",              "message": str}
    """
    answers = answers or []

    # ── Paso 1: Rechazar input vacío (antes de cualquier otra comprobación) ──
    if not text.strip():
        return {
            "status": "invalid",
            "message": "El campo de texto está vacío. Pega el texto del cliente para continuar.",
        }

    # ── Paso 2: Pregunta de identidad (antes del word-count) ─────────────────
    # Las preguntas de identidad son legítimamente cortas; no bloquear por
    # el umbral de palabras mínimas.
    if is_identity_question(text) and not answers:
        return {"status": "identity", "message": get_identity_response()}

    # ── Paso 3: Clasificación determinista (word-count, off-topic) ───────────
    classification = classify_input(text)
    if not classification["valid"]:
        return {"status": "invalid", "message": classification["message"]}

    try:
        # ── Paso 4: Si hay respuestas → Fase 3 directamente ──────────────────
        if answers:
            brief = await generate_brief(text, answers)
            return {"status": "ready", "brief": brief}

        # ── Paso 5: Fase 1 — Extracción ──────────────────────────────────────
        extraction = await extract_fields(text)
        logger.debug("Extraction result: %s", json.dumps(extraction, ensure_ascii=False))

        # ── Paso 6: Comprobar campos críticos ─────────────────────────────────
        missing_critical = get_missing_critical_fields(extraction)

        if not missing_critical:
            # Todos los campos críticos presentes → Fase 3 directamente
            brief = await generate_brief(text, [])
            return {"status": "ready", "brief": brief}

        # ── Paso 7: Fase 2 — Clarificación ───────────────────────────────────
        questions = await generate_questions(text, extraction, missing_critical)
        return {
            "status": "needs_clarification",
            "questions": questions,
        }

    except anthropic.APIConnectionError:
        logger.exception("Connection error calling Anthropic API")
        return {
            "status": "error",
            "message": "No se pudo conectar con el servicio de IA. Comprueba tu conexión e inténtalo de nuevo.",
        }
    except anthropic.AuthenticationError:
        logger.exception("Authentication error calling Anthropic API")
        return {
            "status": "error",
            "message": "Error de autenticación con el servicio de IA. Inténtalo de nuevo o contacta con soporte.",
        }
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.exception("Parsing error in LLM response: %s", exc)
        return {
            "status": "error",
            "message": "El modelo devolvió una respuesta inesperada. Inténtalo de nuevo.",
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error: %s", exc)
        return {
            "status": "error",
            "message": "Error interno del servidor. Inténtalo de nuevo en unos segundos.",
        }
