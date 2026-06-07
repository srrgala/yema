"""
Fase 2 — Clarificación activa.
Genera preguntas específicas para los campos críticos ausentes.
"""

import json
import anthropic

from config import MODEL, BRIEF_FIELDS, MAX_QUESTIONS_PER_ROUND, load_system_prompt

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
---

Devuelve ÚNICAMENTE un array JSON de strings \
(sin bloques de código, sin explicaciones):
["pregunta 1", "pregunta 2"]\
"""


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        raw = "\n".join(inner).strip()
    return raw


async def generate_questions(
    text: str, extraction: dict, missing_critical_fields: list[str]
) -> list[str]:
    """
    Phase 2: Generate targeted questions for missing critical fields.

    Returns:
        List of question strings (max MAX_QUESTIONS_PER_ROUND).
    """
    client = anthropic.AsyncAnthropic()
    system = load_system_prompt()

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
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _clean_json(response.content[0].text)
    questions = json.loads(raw)

    if not isinstance(questions, list):
        questions = []

    # Keep only string entries, cap at max
    return [q for q in questions if isinstance(q, str)][:MAX_QUESTIONS_PER_ROUND]
