"""
Fase 1 — Extracción.
Mapea el texto libre del cliente a los 8 campos del brief.
"""

import json
import anthropic

from config import MODEL, BRIEF_FIELDS, CRITICAL_FIELDS, load_system_prompt

_EXTRACTION_PROMPT = """\
Analiza el siguiente texto de un cliente y extrae información relevante \
para cada campo de un brief de branding.

Reglas estrictas:
- Extrae solo lo que está explícitamente mencionado o muy claramente implicado.
- NO inventes, no supongas, no amplíes más allá de lo dado.
- Si un campo no tiene información en el texto, devuelve null para ese campo.
- Devuelve el texto extraído tal cual, sin reformular.

Campos a extraer:
- context: Historia de la empresa, situación actual, por qué necesitan branding ahora
- mission_vision_values: Para qué existe la empresa, adónde va, qué principios la guían
- objectives: Qué resultado concreto y medible se busca con este trabajo de branding
- target_audience: A quién va dirigida la marca (demografía, psicografía, comportamientos)
- competition: Competidores directos e indirectos, posicionamiento relativo
- brand_personality: Adjetivos, arquetipos, tono de voz, referencias visuales o sonoras
- promise: Promesa de la marca y beneficio diferencial principal
- logistics: Presupuesto, plazos, formatos requeridos, restricciones legales

TEXTO DEL CLIENTE:
---
{text}
---

Devuelve ÚNICAMENTE JSON válido con esta estructura exacta \
(sin bloques de código, sin explicaciones):
{{
  "context": "texto extraído o null",
  "mission_vision_values": "texto extraído o null",
  "objectives": "texto extraído o null",
  "target_audience": "texto extraído o null",
  "competition": "texto extraído o null",
  "brand_personality": "texto extraído o null",
  "promise": "texto extraído o null",
  "logistics": "texto extraído o null"
}}\
"""


def _clean_json(raw: str) -> str:
    """Strip markdown code fences if the model adds them."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first and last fence lines
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        raw = "\n".join(inner).strip()
    return raw


async def extract_fields(text: str) -> dict:
    """
    Phase 1: Extract brief field values from raw client text.

    Returns:
        Dict mapping field keys to extracted strings (or None if absent).
    """
    client = anthropic.AsyncAnthropic()
    system = load_system_prompt()

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[
            {"role": "user", "content": _EXTRACTION_PROMPT.format(text=text)}
        ],
    )

    raw = _clean_json(response.content[0].text)
    data = json.loads(raw)

    # Normalize: ensure all fields present; blank strings → None
    result: dict = {}
    for field in BRIEF_FIELDS:
        value = data.get(field)
        result[field] = value.strip() if isinstance(value, str) and value.strip() else None

    return result


def get_missing_critical_fields(extraction: dict) -> list[str]:
    """Returns critical field keys that are missing (None) in the extraction."""
    return [f for f in CRITICAL_FIELDS if not extraction.get(f)]
