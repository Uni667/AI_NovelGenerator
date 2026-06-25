import pytest
from backend.app.services.local_style_mining_service import (
    generate_style_bible,
    generate_pacing_rules,
    generate_conflict_models,
    generate_hook_models,
    generate_platform_adaptation,
    generate_anti_copy_rules
)

@pytest.fixture
def mock_config(monkeypatch):
    monkeypatch.setenv("MOCK_LLM_MODE", "true")
    
    # Directly monkeypatch the model_runtime creation functions to be bulletproof
    from backend.tests.mock_llm import get_mock_adapter
    monkeypatch.setattr("backend.app.services.model_runtime.create_chat_adapter_from_config", lambda *args, **kwargs: get_mock_adapter())
    
    yield {"provider": "openai", "api_key": "test"}

def test_style_mining_outputs_markdown(mock_config):
    text = "Some random text"
    res = generate_style_bible(text, mock_config)
    assert "# Mock Extraction" in res
    assert "Phase 8" in res

def test_all_mining_functions(mock_config):
    text = "Sample book text"
    
    assert "Mock Extraction" in generate_pacing_rules(text, mock_config)
    assert "Mock Extraction" in generate_conflict_models(text, mock_config)
    assert "Mock Extraction" in generate_hook_models(text, mock_config)
    assert "Mock Extraction" in generate_platform_adaptation(text, mock_config)
    assert "Mock Extraction" in generate_anti_copy_rules(text, mock_config)
