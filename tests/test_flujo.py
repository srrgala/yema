"""
Tests de comportamiento del generador de briefs.

Cobertura:
- Clasificador determinista (sin API)
- Detección de preguntas de identidad (sin API)
- Lógica de campos críticos faltantes (sin API)
- Flujo completo de process_input con LLM mockeado

Ejecutar:
    cd brief-generator
    pytest tests/ -v
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.classifier import classify_input, is_identity_question
from core.extractor import get_missing_critical_fields
from config import CRITICAL_FIELDS


# ── Helpers ───────────────────────────────────────────────────────────────────

VALID_TEXT = (
    "Somos una empresa de consultoría financiera para pymes fundada en 2018. "
    "Operamos en España y queremos redefinir nuestra identidad visual y comunicación "
    "porque sentimos que no transmitimos confianza suficiente a nuestros clientes potenciales. "
    "Nuestro público son directores financieros de empresas de 10 a 50 empleados."
)

SHORT_TEXT = "Hola, quiero hacer branding."


def _make_extraction(**overrides) -> dict:
    """Construct a full extraction dict with all fields None by default."""
    base = {field: None for field in CRITICAL_FIELDS}
    base.update({
        "mission_vision_values": None,
        "competition": None,
        "brand_personality": None,
        "promise": None,
        "logistics": None,
    })
    base.update(overrides)
    return base


class _FakeContentBlock:
    """Minimal stand-in for anthropic.types.ContentBlock."""
    def __init__(self, text: str):
        self.text = text


class _FakeResponse:
    """Minimal stand-in for anthropic.types.Message."""
    def __init__(self, text: str):
        self.content = [_FakeContentBlock(text)]


def _make_anthropic_response(content: str) -> "_FakeResponse":
    """Return a fake Anthropic response with the given text content."""
    return _FakeResponse(content)


# ── Classifier tests ──────────────────────────────────────────────────────────

class TestClassifier:
    def test_empty_string_is_invalid(self):
        result = classify_input("")
        assert result["valid"] is False
        assert result["reason"] == "empty"

    def test_whitespace_only_is_invalid(self):
        result = classify_input("   \n\t  ")
        assert result["valid"] is False
        assert result["reason"] == "empty"

    def test_too_short_is_invalid(self):
        result = classify_input(SHORT_TEXT)
        assert result["valid"] is False
        assert result["reason"] == "too_short"
        assert "20 palabras" in result["message"]

    def test_exactly_20_words_is_valid(self):
        text = " ".join(["palabra"] * 20)
        result = classify_input(text)
        assert result["valid"] is True

    def test_price_query_is_invalid(self):
        result = classify_input(
            "Hola, me interesa saber cuánto cuesta vuestro servicio de branding "
            "para una empresa pequeña como la mía. ¿Tenéis tarifas por proyecto o por horas?"
        )
        assert result["valid"] is False
        assert result["reason"] == "off_topic_price"

    def test_tech_support_is_invalid(self):
        result = classify_input(
            "Tengo un error 404 en mi web cuando intento acceder al panel de administración. "
            "Ya limpié caché y sigo con el mismo problema, necesito soporte urgente."
        )
        assert result["valid"] is False
        assert result["reason"] == "off_topic_tech"

    def test_valid_branding_text(self):
        result = classify_input(VALID_TEXT)
        assert result["valid"] is True
        assert result["reason"] == "ok"
        assert result["message"] is None

    def test_message_is_none_for_valid_input(self):
        result = classify_input(VALID_TEXT)
        assert result["message"] is None


# ── Identity detection tests ──────────────────────────────────────────────────

class TestIdentityDetection:
    def test_qué_eres_is_identity(self):
        assert is_identity_question("qué eres") is True

    def test_cómo_funcionas_is_identity(self):
        assert is_identity_question("cómo funcionas exactamente") is True

    def test_para_qué_sirves_is_identity(self):
        assert is_identity_question("para qué sirves") is True

    def test_ayuda_is_identity(self):
        assert is_identity_question("ayuda") is True

    def test_long_text_not_identity(self):
        # Texts longer than 30 words are never identity questions
        # "qué eres" = 2 words → need 16+ repetitions for > 30 words
        long = ("qué eres " * 16).strip()  # 32 words
        assert is_identity_question(long) is False

    def test_valid_client_text_not_identity(self):
        assert is_identity_question(VALID_TEXT) is False


# ── Missing critical fields tests ─────────────────────────────────────────────

class TestMissingCriticalFields:
    def test_all_critical_missing(self):
        extraction = _make_extraction()
        missing = get_missing_critical_fields(extraction)
        assert set(missing) == set(CRITICAL_FIELDS)

    def test_none_missing(self):
        extraction = _make_extraction(
            context="Empresa de consultoría fundada en 2010.",
            objectives="Incrementar reconocimiento de marca en un 30%.",
            target_audience="Pymes de 10-50 empleados del sector industrial.",
        )
        assert get_missing_critical_fields(extraction) == []

    def test_partial_missing(self):
        extraction = _make_extraction(
            context="Empresa de consultoría fundada en 2010.",
            # objectives and target_audience still None
        )
        missing = get_missing_critical_fields(extraction)
        assert "objectives" in missing
        assert "target_audience" in missing
        assert "context" not in missing

    def test_empty_string_treated_as_missing(self):
        extraction = _make_extraction(context="   ", objectives=None, target_audience=None)
        # extractor normalizes empty strings to None; here we test logic directly
        # empty string is falsy so it counts as missing
        extraction["context"] = ""
        missing = get_missing_critical_fields(extraction)
        assert "context" in missing


# ── Orchestrator (process_input) tests ───────────────────────────────────────

class TestProcessInput:
    """
    These tests mock the Anthropic client so no real API calls are made.
    """

    @pytest.mark.asyncio
    async def test_invalid_input_returns_invalid_status(self):
        from main import process_input
        result = await process_input("muy corto")
        assert result["status"] == "invalid"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_identity_question_returns_identity_status(self):
        from main import process_input
        result = await process_input("qué eres")
        assert result["status"] == "identity"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_needs_clarification_when_critical_fields_missing(self):
        # All critical fields missing in extraction
        extraction_all_null = {field: None for field in [
            "context", "mission_vision_values", "objectives", "target_audience",
            "competition", "brand_personality", "promise", "logistics",
        ]}
        expected_questions = [
            "¿Cuál es la historia de tu empresa?",
            "¿Qué resultado concreto buscáis con este proyecto de branding?",
            "¿A quién va dirigida vuestra marca?",
        ]

        # Patch at main.py's import boundary for maximum reliability
        with patch("main.extract_fields", new_callable=AsyncMock, return_value=extraction_all_null), \
             patch("main.generate_questions", new_callable=AsyncMock, return_value=expected_questions):

            from main import process_input
            result = await process_input(VALID_TEXT)

        assert result["status"] == "needs_clarification"
        assert isinstance(result["questions"], list)
        assert len(result["questions"]) > 0

    @pytest.mark.asyncio
    async def test_ready_when_all_critical_fields_present(self):
        extraction_with_criticals = {
            "context": "Empresa de consultoría fundada en 2010.",
            "mission_vision_values": None,
            "objectives": "Incrementar reconocimiento de marca un 30%.",
            "target_audience": "Directores financieros de pymes.",
            "competition": None,
            "brand_personality": None,
            "promise": None,
            "logistics": None,
        }
        expected_brief = {
            "context": "Empresa de consultoría con trayectoria consolidada desde 2010.",
            "mission_vision_values": "(no proporcionado)",
            "objectives": "Incrementar reconocimiento de marca en un 30% en 12 meses.",
            "target_audience": "Directores financieros de empresas de 10-50 empleados.",
            "competition": "(no proporcionado)",
            "brand_personality": "(inferido — pendiente de validación)",
            "promise": "(inferido — pendiente de validación)",
            "logistics": "(no proporcionado)",
        }

        with patch("main.extract_fields", new_callable=AsyncMock, return_value=extraction_with_criticals), \
             patch("main.generate_brief", new_callable=AsyncMock, return_value=expected_brief):

            from main import process_input
            result = await process_input(VALID_TEXT)

        assert result["status"] == "ready"
        assert "brief" in result
        assert isinstance(result["brief"], dict)
        assert "context" in result["brief"]

    @pytest.mark.asyncio
    async def test_with_answers_skips_to_generation(self):
        """When answers are provided, extract is skipped and we go straight to Phase 3."""
        expected_brief = {
            "context": "Empresa de consultoría con trayectoria consolidada.",
            "mission_vision_values": "(inferido — pendiente de validación)",
            "objectives": "Conseguir 20 nuevos clientes en 6 meses.",
            "target_audience": "Pymes del sector industrial.",
            "competition": "(no proporcionado)",
            "brand_personality": "Confiable, cercano, experto.",
            "promise": "(inferido — pendiente de validación)",
            "logistics": "(no proporcionado)",
        }

        answers = [
            {"question": "¿Cuál es el objetivo?", "answer": "Conseguir 20 nuevos clientes en 6 meses."},
            {"question": "¿A quién os dirigís?",  "answer": "Pymes del sector industrial."},
        ]

        with patch("main.generate_brief", new_callable=AsyncMock, return_value=expected_brief):
            from main import process_input
            result = await process_input(VALID_TEXT, answers=answers)

        assert result["status"] == "ready"
        assert "brief" in result
