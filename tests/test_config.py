import importlib
import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _reload_config_module():
    import src.config as config_module

    return importlib.reload(config_module)


def test_collect_settings_errors_should_report_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_PROVIDERS", "deepseek,gemini")
    monkeypatch.setenv("JARVIS_DEFAULT_PROVIDER", "openai")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "")
    monkeypatch.setenv("DEEPSEEK_MODEL", "")
    monkeypatch.setenv("GEMINI_BASE_URL", "")
    monkeypatch.setenv("GEMINI_MODEL", "")
    monkeypatch.setenv("JARVIS_LLM_MAX_RETRIES", "-1")
    monkeypatch.setenv("JARVIS_MAX_ITERATIONS", "0")
    monkeypatch.setenv("JARVIS_TOOL_MAX_RETRIES", "-2")

    config = _reload_config_module()
    errors = config.collect_settings_errors()
    assert len(errors) >= 7
    assert any("JARVIS_DEFAULT_PROVIDER" in item for item in errors)
    assert any("DEEPSEEK_BASE_URL" in item for item in errors)
    assert any("GEMINI_MODEL" in item for item in errors)
    assert any("JARVIS_LLM_MAX_RETRIES" in item for item in errors)
    assert any("JARVIS_MAX_ITERATIONS" in item for item in errors)
    assert any("JARVIS_TOOL_MAX_RETRIES" in item for item in errors)


def test_validate_settings_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_PROVIDERS", "deepseek")
    monkeypatch.setenv("JARVIS_DEFAULT_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "dummy")
    monkeypatch.setenv("JARVIS_LLM_MAX_RETRIES", "1")
    monkeypatch.setenv("JARVIS_MAX_ITERATIONS", "5")
    monkeypatch.setenv("JARVIS_TOOL_MAX_RETRIES", "1")

    config = _reload_config_module()
    config.validate_settings()

