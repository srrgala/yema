"""
Fase 3 — Generación del brief.
Produce el brief estructurado a partir de toda la información disponible.
"""

import anthropic

from config import MODEL, BRIEF_FIELDS, load_system_prompt

# Cargado una vez al arranque del módulo, no en cada request.
_SYSTEM_PROMPT: str = load_system_prompt()

_GENERATION_TOOL = {
    "name": "generate_brief",
    "description": "Genera el brief de branding estructurado con los 8 campos desarrollados.",
    "input_schema": {
        "type": "object",
        "properties": {
            "context": {
                "type": "string",
                "description": "Contexto y antecedentes: historia, situación actual, motivación del proyecto.",
            },
            "mission_vision_values": {
                "type": "string",
                "description": "Misión, visión y valores de la empresa.",
            },
            "objectives": {
                "type": "string",
                "description": "Objetivos concretos y medibles del proyecto de branding.",
            },
            "target_audience": {
                "type": "string",
                "description": "Público objetivo: demografía, psicografía, comportamientos.",
            },
            "competition": {
                "type": "string",
                "description": "Análisis de competidores directos e indirectos, posicionamiento relativo.",
            },
            "brand_personality": {
                "type": "string",
                "description": "Personalidad de la marca: adjetivos, arquetipos, tono, referencias.",
            },
            "promise": {
                "type": "string",
                "description": "Promesa de la marca y beneficio diferencial principal.",
            },
            "logistics": {
                "type": "string",
                "description": "Restricciones y requisitos logísticos: presupuesto, plazos, formatos.",
            },
        },
        "required": [
            "context", "mission_vision_values", "objectives", "target_audience",
            "competition", "brand_personality", "promise", "logistics",
        ],
    },
}

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
estratégico profesional. No añadas secciones ni campos extra.\
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

    prompt = _GENERATION_PROMPT.format(
        original_text=original_text,
        clarifications_block=_format_clarifications(answers),
    )

    response = await client.messages.create(
        model=MODEL,
        max_tokens=2500,
        system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        tools=[_GENERATION_TOOL],
        tool_choice={"type": "tool", "name": "generate_brief"},
        messages=[{"role": "user", "content": prompt}],
    )

    tool_block = next(b for b in response.content if b.type == "tool_use")
    data = tool_block.input  # dict Python ya parseado — sin json.loads(), sin _clean_json()

    result: dict = {}
    for field in BRIEF_FIELDS:
        value = data.get(field, "(no proporcionado)")
        result[field] = value if isinstance(value, str) and value.strip() else "(no proporcionado)"

    return result
