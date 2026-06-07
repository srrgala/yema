"""
Fase 3 — Generación del brief.
Produce el brief estructurado a partir de toda la información disponible.
"""

import json
import anthropic

from config import MODEL, BRIEF_FIELDS, load_system_prompt

_GENERATION_PROMPT = """\
Genera un brief de branding completo y profesional basándote en \
toda la información disponible a continuación.

TEXTO ORIGINAL DEL CLIENTE:
---
{original_text}
---
{clarifications_block}
Instrucciones por campo:
- Información proporcionada explícitamente → desarróllala con profundidad \
estratégica (2-4 párrafos según la riqueza del dato).
- Información que se puede inferir razonablemente del contexto → \
desarróllala y añade al final "(inferido — pendiente de validación)".
- Información completamente ausente → escribe únicamente "(no proporcionado)".

No repitas verbatim el texto del cliente; transfórmalo en lenguaje \
estratégico profesional. No añadas secciones ni campos extra.

Devuelve ÚNICAMENTE JSON válido con esta estructura exacta \
(sin bloques de código, sin explicaciones):
{{
  "context": "contenido",
  "mission_vision_values": "contenido",
  "objectives": "contenido",
  "target_audience": "contenido",
  "competition": "contenido",
  "brand_personality": "contenido",
  "promise": "contenido",
  "logistics": "contenido"
}}\
"""

_CLARIFICATIONS_TEMPLATE = """\

ACLARACIONES DEL CLIENTE:
---
{qa_block}
---
"""


def _format_clarifications(answers: list[dict]) -> str:
    if not answers:
        return ""
    lines = []
    for i, item in enumerate(answers, 1):
        q = item.get("question", "").strip()
        a = item.get("answer", "").strip()
        if q and a:
            lines.append(f"P{i}: {q}")
            lines.append(f"R{i}: {a}")
            lines.append("")
    if not lines:
        return ""
    return _CLARIFICATIONS_TEMPLATE.format(qa_block="\n".join(lines).rstrip())


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        raw = "\n".join(inner).strip()
    return raw


async def generate_brief(original_text: str, answers: list[dict]) -> dict:
    """
    Phase 3: Generate the structured branding brief.

    Args:
        original_text: Raw client input from Phase 1.
        answers: List of {question, answer} dicts from the clarification round.

    Returns:
        Dict mapping field keys to developed content strings.
    """
    client = anthropic.AsyncAnthropic()
    system = load_system_prompt()

    prompt = _GENERATION_PROMPT.format(
        original_text=original_text,
        clarifications_block=_format_clarifications(answers),
    )

    response = await client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _clean_json(response.content[0].text)
    data = json.loads(raw)

    result: dict = {}
    for field in BRIEF_FIELDS:
        value = data.get(field, "(no proporcionado)")
        result[field] = value if isinstance(value, str) and value.strip() else "(no proporcionado)"

    return result
