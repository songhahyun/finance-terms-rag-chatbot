from __future__ import annotations

from src.common.config import get_settings


def test_intent_classifier_settings_read_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("INTENT_CLASSIFIER_PROVIDER", "openai")
    monkeypatch.setenv("INTENT_CLASSIFIER_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("INTENT_CLASSIFIER_TIMEOUT", "3.5")
    monkeypatch.setenv("INTENT_CLASSIFIER_CONFIDENCE_THRESHOLD", "0.8")

    settings = get_settings()

    assert settings.intent_classifier_provider == "openai"
    assert settings.intent_classifier_model == "gpt-4.1-mini"
    assert settings.intent_classifier_timeout == 3.5
    assert settings.intent_classifier_confidence_threshold == 0.8
