from pathlib import Path

BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompts"

# LLM
MODEL = "claude-haiku-4-5-20251001"


def load_system_prompt() -> str:
    return (PROMPTS_DIR / "system_prompt.txt").read_text(encoding="utf-8")


# Brief field definitions (insertion order = display order)
BRIEF_FIELDS: dict[str, dict] = {
    "context": {
        "name": "Contexto y antecedentes",
        "description": "Historia de la empresa, situación actual, por qué necesitan branding ahora",
        "critical": True,
        "inferable": False,
    },
    "mission_vision_values": {
        "name": "Misión, Visión y Valores",
        "description": "Para qué existe la empresa, adónde va, qué principios la guían",
        "critical": False,
        "inferable": True,
    },
    "objectives": {
        "name": "Objetivos del proyecto",
        "description": "Qué resultado concreto y medible se busca con este trabajo de branding",
        "critical": True,
        "inferable": False,
    },
    "target_audience": {
        "name": "Público objetivo (Target y Buyer Persona)",
        "description": "A quién va dirigida la marca: demografía, psicografía, comportamientos",
        "critical": True,
        "inferable": False,
    },
    "competition": {
        "name": "Análisis de la competencia",
        "description": "Competidores directos e indirectos, posicionamiento relativo",
        "critical": False,
        "inferable": False,
    },
    "brand_personality": {
        "name": "Personalidad de la marca",
        "description": "Adjetivos, arquetipos, tono de voz, referencias visuales o sonoras",
        "critical": False,
        "inferable": True,
    },
    "promise": {
        "name": "Promesa y beneficio principal",
        "description": "Qué promete la marca a su cliente ideal y qué beneficio diferencial ofrece",
        "critical": False,
        "inferable": True,
    },
    "logistics": {
        "name": "Restricciones y requisitos logísticos",
        "description": "Presupuesto, plazos, formatos requeridos, restricciones legales",
        "critical": False,
        "inferable": False,
    },
}

CRITICAL_FIELDS: list[str] = [k for k, v in BRIEF_FIELDS.items() if v["critical"]]
INFERABLE_FIELDS: list[str] = [k for k, v in BRIEF_FIELDS.items() if v.get("inferable")]

# Input validation
MIN_WORDS = 20
MAX_QUESTIONS_PER_ROUND = 3

# Deterministic out-of-context patterns (lowercase, checked with 'in')
PRICE_PATTERNS = [
    "cuánto cuesta",
    "cuanto cuesta",
    "qué precio tiene",
    "que precio tiene",
    "cuál es la tarifa",
    "cual es la tarifa",
    "presupuesto del servicio",
    "cuánto cobráis",
    "cuanto cobran",
    "precio de vuestro servicio",
    "cuánto vale contrataros",
]

TECH_SUPPORT_PATTERNS = [
    "error 404",
    "error 500",
    "error 403",
    "no funciona la web",
    "bug en",
    "api key inválida",
    "api key invalida",
    "token expired",
    "crash",
    "falla el sistema",
    "problema técnico",
    "soporte técnico",
]

IDENTITY_PATTERNS = [
    "qué eres",
    "que eres",
    "quién eres",
    "quien eres",
    "qué haces",
    "que haces",
    "cómo funcionas",
    "como funcionas",
    "para qué sirves",
    "para que sirves",
    "qué puedo hacer aquí",
    "que puedo hacer",
    "ayuda",
    "instrucciones",
    "cómo te uso",
    "como te uso",
]
