"""
Fase 1 — Extracción.
Mapea el texto libre del cliente a los 8 campos del brief.
"""

import anthropic

from config import MODEL, BRIEF_FIELDS, CRITICAL_FIELDS, load_system_prompt

# Cargado una vez al arranque del módulo, no en cada request.
_SYSTEM_PROMPT: str = load_system_prompt()

_EXTRACTION_TOOL = {
    "name": "extract_brief_fields",
    "description": "Extrae los campos del brief de branding a partir del texto del cliente.",
    "input_schema": {
        "type": "object",
        "properties": {
            "context": {
                "type": ["string", "null"],
                "description": "Historia de la empresa, situación actual, por qué necesitan branding ahora.",
            },
            "mission_vision_values": {
                "type": ["string", "null"],
                "description": "Para qué existe la empresa, adónde va, qué principios la guían.",
            },
            "objectives": {
                "type": ["string", "null"],
                "description": "Qué resultado concreto y medible se busca con este trabajo de branding.",
            },
            "target_audience": {
                "type": ["string", "null"],
                "description": "A quién va dirigida la marca: demografía, psicografía, comportamientos.",
            },
            "competition": {
                "type": ["string", "null"],
                "description": "Competidores directos e indirectos, posicionamiento relativo.",
            },
            "brand_personality": {
                "type": ["string", "null"],
                "description": "Adjetivos, arquetipos, tono de voz, referencias visuales o sonoras.",
            },
            "promise": {
                "type": ["string", "null"],
                "description": "Promesa de la marca y beneficio diferencial principal.",
            },
            "logistics": {
                "type": ["string", "null"],
                "description": "Presupuesto, plazos, formatos requeridos, restricciones legales.",
            },
        },
        "required": [
            "context", "mission_vision_values", "objectives", "target_audience",
            "competition", "brand_personality", "promise", "logistics",
        ],
    },
}

_EXTRACTION_PROMPT = """\
Analiza el siguiente texto de un cliente y extrae información relevante \
para cada campo del brief de branding.

Reglas estrictas:
- Extrae solo lo que está explícitamente mencionado o muy claramente implicado.
- NO inventes, no supongas, no amplíes más allá de lo dado.
- Si un campo no tiene información en el texto, devuelve null para ese campo.
- Devuelve el texto extraído tal cual, sin reformular.

TEXTO DEL CLIENTE:
---
{text}
---\
"""


async def extract_fields(text: str) -> dict:
    """
    Phase 1: Extract brief field values from raw client text.

    Returns:
        Dict mapping field keys to extracted strings (or None if absent).
    """
    client = anthropic.AsyncAnthropic()

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        tools=[_EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "extract_brief_fields"},
        messages=[{"role": "user", "content": _EXTRACTION_PROMPT.format(text=text)}],
    )

    tool_block = next(b for b in response.content if b.type == "tool_use")
    data = tool_block.input  # dict Python ya parseado — sin json.loads(), sin _clean_json()

    result: dict = {}
    for field in BRIEF_FIELDS:
        value = data.get(field)
        result[field] = value.strip() if isinstance(value, str) and value.strip() else None

    return result


def get_missing_critical_fields(extraction: dict) -> list[str]:
    """Returns critical field keys that are missing (None) in the extraction."""
    return [f for f in CRITICAL_FIELDS if not extraction.get(f)]
