"""
Respuesta de identidad del sistema.
No requiere llamada al LLM.
"""

IDENTITY_RESPONSE = """\
Soy un **generador de briefs de branding**. Convierto textos desordenados de clientes \
—emails, documentos, notas— en briefs estratégicos estructurados y accionables.

**Cómo funciono en tres fases:**

1. **Extracción** — Analizo el texto del cliente y mapeo toda la información \
a los 8 campos del brief.
2. **Clarificación** — Si faltan datos críticos (contexto, objetivos o público objetivo), \
te hago hasta 3 preguntas concretas para completarlos.
3. **Generación** — Con la información completa, produzco un brief profesional. \
Lo inferido se marca explícitamente; lo ausente, también.

**Para empezar:** pega el texto del cliente en el área de texto y haz clic en *Procesar*.\
"""


def get_identity_response() -> str:
    return IDENTITY_RESPONSE
