import pytest
from backend.app.services.local_scene_pattern_service import (
    generate_scene_patterns,
    generate_plot_structure,
    generate_character_arcs
)

@pytest.fixture
def mock_config(monkeypatch):
    monkeypatch.setenv("MOCK_LLM_MODE", "true")
    
    from backend.tests.mock_llm import get_mock_adapter
    monkeypatch.setattr("backend.app.services.model_runtime.create_chat_adapter_from_config", lambda *args, **kwargs: get_mock_adapter())
    
    yield {"provider": "openai", "api_key": "test"}

def test_generate_scene_patterns_returns_json(mock_config):
    text = "Some random text"
    patterns = generate_scene_patterns(text, mock_config)
    assert isinstance(patterns, list)
    assert len(patterns) > 0
    assert "pattern_name" in patterns[0]
    assert patterns[0]["pattern_name"] == "打脸"

def test_generate_plot_and_character(mock_config):
    text = "Sample book text"
    assert "Mock Extraction" in generate_plot_structure(text, mock_config)
    assert "Mock Extraction" in generate_character_arcs(text, mock_config)
