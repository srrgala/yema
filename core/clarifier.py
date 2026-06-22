"""
Fase 2 — Clarificación activa.
Genera preguntas específicas para los campos críticos ausentes.
"""

import json

import anthropic

from config import MODEL, BRIEF_FIELDS, MAX_QUESTIONS_PER_ROUND, load_system_prompt

# Cargado una vez al arranque del módulo, no en cada request.
_SYSTEM_PROMPT: str = load_system_prompt()

_CLARIFICATION_TOOL = {
    "name": "generate_clarification_questions",
    "description": "Genera preguntas de clarificación para los campos críticos ausentes en el brief.",
    "input_schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    f"Lista de preguntas (máximo {MAX_QUESTIONS_PER_ROUND}). "
                    "Cada una directa, accionable, apuntando a un único dato."
                ),
            }
        },
        "required": ["questions"],
    },
}

_CLARIFICATION_PROMPT = """\
El texto del cliente está incompleto. Faltan datos en campos críticos \
que impiden generar un brief útil:

{missing_fields_block}

Tu tarea: genera preguntas específicas y concretas para obtener esos datos.

Reglas:
- Máximo {max_questions} preguntas en total.
- Cada pregunta debe ser directa, accionable y apuntar a un único dato.
- NO preguntes sobre información que ya está en el texto del cliente.
- Usa un tono profesional y cercano ("tu empresa", "vuestro").
- Las preguntas deben ser lo suficientemente concretas para que el cliente \
responda en 1-3 frases.

TEXTO ORIGINAL DEL CLIENTE:
---
{text}
---\
"""


async def generate_questions(
    text: str, extraction: dict, missing_critical_fields: list[str]
) -> list[str]:
    """
    Phase 2: Generate targeted questions for missing critical fields.

    Returns:
        List of question strings (max MAX_QUESTIONS_PER_ROUND).
    """
    client = anthropic.AsyncAnthropic()

    missing_lines = []
    for field in missing_critical_fields:
        info = BRIEF_FIELDS[field]
        missing_lines.append(f"- **{info['name']}**: {info['description']}")

    prompt = _CLARIFICATION_PROMPT.format(
        missing_fields_block="\n".join(missing_lines),
        max_questions=MAX_QUESTIONS_PER_ROUND,
        text=text,
    )

    response = await client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        tools=[_CLARIFICATION_TOOL],
        tool_choice={"type": "tool", "name": "generate_clarification_questions"},
        messages=[{"role": "user", "content": prompt}],
    )
    print(json.dumps({
        "proyecto": "yema",
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0),
        "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0),
    }))

    tool_block = next(b for b in response.content if b.type == "tool_use")
    questions = tool_block.input.get("questions", [])

    return [q for q in questions if isinstance(q, str)][:MAX_QUESTIONS_PER_ROUND]
