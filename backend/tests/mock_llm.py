import json
import os
from typing import Any

# Global state to control mock scenarios
MOCK_SCENARIO = "normal"
MOCK_LLM_MODE = os.environ.get("MOCK_LLM_MODE", "false").lower() == "true"

class MockChatModel:
    def __init__(self, *args, **kwargs):
        self.temperature = 0.5
        pass
        
    def __call__(self, messages: list, **kwargs) -> Any:
        return MockAIMessage(self.invoke(messages, **kwargs))

    def invoke(self, prompt: str, **kwargs) -> str:
        global MOCK_SCENARIO
        
        # Determine the type of request based on prompt content
        if "状态管理 AI" in str(prompt) or "State Patch" in str(prompt):
            return self._mock_state_patch(str(prompt))
        elif "小说结构编辑" in str(prompt) or "outline_diff" in str(prompt):
            return self._mock_outline_evolution(str(prompt))
        elif "场景模式" in str(prompt) or "scene_patterns" in str(prompt):
            return self._mock_scene_patterns(str(prompt))
        elif "只提炼写法" in str(prompt):
            return self._mock_style_mining(str(prompt))
        elif "请根据前文设定和上下文" in str(prompt) or "Draft Generation" in str(prompt) or "写一章" in str(prompt):
            return self._mock_draft_generation(str(prompt))
        elif "Title Generation" in str(prompt) or "书名" in str(prompt):
            return "测试书名1\n测试书名2\n测试书名3"
        elif "Summary Generation" in str(prompt) or "简介" in str(prompt):
            return "这是一个测试简介，没有剧透未揭露的秘密。"
        
        return "Generic Mock Response"

    def _mock_scene_patterns(self, prompt: str) -> str:
        return '''```json
[
  {
    "pattern_name": "打脸",
    "description": "反派嘲讽，主角反击",
    "trigger": "反派出现",
    "resolution": "主角展现实力"
  }
]
```'''

    def _mock_style_mining(self, prompt: str) -> str:
        return "# Mock Extraction\nThis is a mock analysis for Phase 8."

    def _mock_state_patch(self, prompt: str) -> str:
        if MOCK_SCENARIO == "invalid_json":
            return "This is not valid json { [ "
            
        is_high_risk = MOCK_SCENARIO in ["shisi_uncle_name_revealed", "high_risk_patch"]
        
        patch = {
            "summary_update": "十四叔本章现身",
            "new_characters": [],
            "character_updates": [],
            "relationship_updates": [],
            "name_usage_updates": [],
            "revealed_secrets": [],
            "new_secrets": [],
            "plot_progress": ["推进了一点剧情"],
            "new_plot_threads": [],
            "resolved_plot_threads": [],
            "worldbuilding_updates": [],
            "continuity_warnings": [],
            "next_chapter_notes": []
        }
        
        if MOCK_SCENARIO == "shisi_uncle_name_revealed":
            patch["character_updates"].append({
                "id": "char_shisi",
                "true_name": "林惊羽",
                "true_name_revealed_to_reader": True,
                "current_status": "活跃"
            })
            patch["revealed_secrets"].append("十四叔的真名是林惊羽")
        elif MOCK_SCENARIO == "bad_name_leak":
            patch["continuity_warnings"].append("旁白在未揭露前泄露了真名")
            
        return "```json\n" + json.dumps(patch) + "\n```"

    def _mock_outline_evolution(self, prompt: str) -> str:
        if MOCK_SCENARIO == "invalid_json":
            return "bad json"
            
        diff = {
            "summary": "Mock Outline Diff",
            "affected_chapters": [12],
            "changes": []
        }
        
        if MOCK_SCENARIO == "outline_conflict":
            diff["changes"].append({
                "chapter_index": 12,
                "change_type": "modify",
                "field": "chapter_goal",
                "before": "首次揭露十四叔本名",
                "after": "利用旧名施压",
                "reason": "第5章已揭名，修复冲突",
                "risk_level": "high"
            })
            
        return "```json\n" + json.dumps(diff) + "\n```"

    def _mock_draft_generation(self, prompt: str) -> str:
        if MOCK_SCENARIO == "shisi_uncle_name_revealed":
            return "十四叔低声道：“我本名林惊羽。”他环顾四周，目光如炬。"
        elif MOCK_SCENARIO == "shisi_uncle_unrevealed":
            return "十四叔沉默不语，只是擦拭着手中的剑。"
        elif MOCK_SCENARIO == "bad_name_leak":
            return "林惊羽（即十四叔）走进了大殿。"
            
        return "这是一段正常的测试章节草稿内容。"

class MockAIMessage:
    def __init__(self, content):
        self.content = content

class MockAdapter:
    def __init__(self):
        self.model = MockChatModel()
        
    def invoke(self, prompt):
        return self.model.invoke(prompt)

def get_mock_adapter():
    return MockAdapter()

# We will provide a context manager to patch `_build_chat_adapter` across the app
from contextlib import contextmanager
from unittest.mock import patch

@contextmanager
def patch_llm_for_tests():
    global MOCK_LLM_MODE
    original = MOCK_LLM_MODE
    MOCK_LLM_MODE = True
    
    class DummyConfig:
        pass
        
    with patch("backend.app.services.model_runtime._build_chat_adapter") as mock_build, \
         patch("backend.app.services.model_runtime.create_chat_adapter_from_config") as mock_create, \
         patch("backend.app.services.config_resolver.get_runtime_config") as mock_config:
        mock_build.return_value = get_mock_adapter()
        mock_create.return_value = get_mock_adapter()
        mock_config.return_value = DummyConfig()
        yield
    MOCK_LLM_MODE = original
