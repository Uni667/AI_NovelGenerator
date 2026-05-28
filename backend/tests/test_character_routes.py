import pytest
import json
import os
from unittest.mock import MagicMock

class MockLLM:
    def __init__(self, response_text):
        self.response_text = response_text
    def invoke(self, prompt, **kwargs):
        return self.response_text

@pytest.fixture
def mock_planning_llm(monkeypatch):
    mock_response = json.dumps({
        "characters": [
            {"name": "规划角色A", "description": "规划角色A的描述", "first_appearance_chapter": 1},
            {"name": "规划角色B", "description": "规划角色B的描述", "first_appearance_chapter": 2}
        ],
        "outline": "1: 第一章故事\n2: 第二章故事"
    })
    mock_adapter = MockLLM(mock_response)
    monkeypatch.setattr(
        "backend.app.services.model_runtime._build_chat_adapter",
        lambda *args, **kwargs: mock_adapter
    )
    return mock_adapter

def test_plan_characters_route(client, auth_headers, test_project, mock_planning_llm, monkeypatch):
    # Mock runtime config to avoid ConfigError
    mock_config = MagicMock()
    mock_config.temperature = 0.7
    mock_config.max_tokens = 2000
    monkeypatch.setattr(
        "backend.app.services.config_resolver.get_runtime_config",
        lambda *args, **kwargs: mock_config
    )

    # 准备环境：写入 Novel_architecture.txt
    os.makedirs(test_project["filepath"], exist_ok=True)
    with open(os.path.join(test_project["filepath"], "Novel_architecture.txt"), "w", encoding="utf-8") as f:
        f.write("测试架构内容")

    url = f"/api/v1/projects/{test_project['id']}/characters/plan"
    response = client.post(url, headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "characters" in data
    assert "outline" in data
    assert len(data["characters"]) == 2
    assert data["characters"][0]["name"] == "规划角色A"
    assert data["outline"] == "1: 第一章故事\n2: 第二章故事"
