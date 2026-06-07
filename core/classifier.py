"""
Clasificador determinista pre-LLM.
Rechaza inputs inválidos o fuera de contexto sin gastar tokens de API.
"""

from config import MIN_WORDS, PRICE_PATTERNS, TECH_SUPPORT_PATTERNS, IDENTITY_PATTERNS


def classify_input(text: str) -> dict:
    """
    Analiza el texto de entrada y determina si es procesable.

    Returns:
        {"valid": bool, "reason": str, "message": str | None}
    """
    stripped = text.strip()

    if not stripped:
        return {
            "valid": False,
            "reason": "empty",
            "message": "El campo de texto está vacío. Pega el texto del cliente para continuar.",
        }

    word_count = len(stripped.split())
    if word_count < MIN_WORDS:
        return {
            "valid": False,
            "reason": "too_short",
            "message": (
                f"El texto es demasiado corto ({word_count} palabras). "
                f"Necesitamos al menos {MIN_WORDS} palabras para identificar "
                "información relevante para el brief."
            ),
        }

    text_lower = stripped.lower()

    for pattern in PRICE_PATTERNS:
        if pattern in text_lower:
            return {
                "valid": False,
                "reason": "off_topic_price",
                "message": (
                    "Parece una consulta sobre precios o tarifas. "
                    "Este sistema procesa textos de clientes para generar briefs de branding estratégico."
                ),
            }

    for pattern in TECH_SUPPORT_PATTERNS:
        if pattern in text_lower:
            return {
                "valid": False,
                "reason": "off_topic_tech",
                "message": (
                    "Parece una consulta de soporte técnico. "
                    "Este sistema procesa textos de clientes para generar briefs de branding estratégico."
                ),
            }

    return {"valid": True, "reason": "ok", "message": None}


def is_identity_question(text: str) -> bool:
    """
    Detecta si el input es una pregunta sobre qué es o qué hace el sistema.
    Solo aplica a textos cortos (< 30 palabras).
    """
    stripped = text.strip()
    if len(stripped.split()) > 30:
        return False
    text_lower = stripped.lower()
    return any(pattern in text_lower for pattern in IDENTITY_PATTERNS)
