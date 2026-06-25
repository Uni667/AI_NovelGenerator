import os
import json
import pytest
from backend.app.services.local_similarity_guard_service import (
    analyze_similarity,
    save_similarity_report,
    get_consecutive_overlap
)
from novel_generator.chapter import generate_chapter_draft

class DummyLLM:
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0
        
    def invoke(self, messages, *args, **kwargs):
        resp = self.responses[min(self.call_count, len(self.responses) - 1)]
        self.call_count += 1
        return resp

class DummyContext:
    def __init__(self, project_id, filepath, llm_adapter):
        self.project_id = project_id
        self.filepath = filepath
        self.cancel_token = None
        self.user_id = "test_user"
        
        class DummyLLMConfig:
            interface_format = "openai"
            base_url = ""
            model_name = "test"
            api_key = ""
            temperature = 0.7
            max_tokens = 1000
            timeout = 30
        self.llm = DummyLLMConfig()
        


class DummyParams:
    def __init__(self):
        self.chapter_number = 1
        self.word_number = 1000
        self.characters_involved = ""
        self.key_items = ""
        self.scene_location = ""
        self.time_constraint = ""
        self.user_guidance = ""

@pytest.fixture
def test_workspace(tmp_path):
    project_id = "test_guard_project"
    filepath = str(tmp_path)
    os.makedirs(os.path.join(filepath, "chapters"), exist_ok=True)
    return project_id, filepath

def test_similarity_analyzer():
    ref_texts = [
        "在这个世界上，有一把被称为轩辕剑的绝世兵器。它散发着金色的光芒，拥有毁天灭地的力量。",
        "“你休想逃走！”主角大喊一声，拔出长剑冲了上去。"
    ]
    
    # 1. 相似段落命中（n-gram 或者 consecutive）
    gen_text_high = "在这个世界上，有一把被称为轩辕剑的绝世兵器。它散发着金色的光芒，拥有毁天灭地的力量。这个描述完全一样。我们看看会不会触发。必须凑够50字以上的连贯。在这个世界上，有一把被称为轩辕剑的绝世兵器。它散发着金色的光芒，拥有毁天灭地的力量。" * 2
    report_high = analyze_similarity(gen_text_high, ref_texts, "proj_1")
    assert report_high["needs_rewrite"] is True
    assert report_high["max_ngram_overlap_ratio"] > 0.05 or report_high["long_sentence_match_count"] > 3 or "存在超过 50 字的连续原文复制" in report_high["reasons"]
    
    # 2. 正常段落通过
    gen_text_ok = "那是一把古老的铁剑，剑身锈迹斑斑。虽然看起来不起眼，但据说曾经属于一位传说中的英雄。少年握紧剑柄，眼神坚定，他知道接下来的路不会平坦。"
    report_ok = analyze_similarity(gen_text_ok, ref_texts, "proj_1")
    assert report_ok["needs_rewrite"] is False
    assert report_ok["max_ngram_overlap_ratio"] < 0.05
    
    # 3. 专有名词过多命中 (Mock提取的是「」、“”、《》的内容)
    gen_text_noun = "我们有“你休想逃走！”也有“你休想逃走！”还有“你休想逃走！”" * 10
    report_noun = analyze_similarity(gen_text_noun, ref_texts, "proj_1")
    assert report_noun["needs_rewrite"] is True
    assert "长句重复" in report_noun["rewrite_instruction"] or "n-gram" in report_noun["rewrite_instruction"] or "连续原文复制" in report_noun["rewrite_instruction"]

def test_report_does_not_contain_original_text(tmp_path):
    ref_texts = ["这是一段极度机密的参考书文本，绝对不能泄露。"]
    gen_text = "这是一段极度机密的参考书文本，绝对不能泄露。" * 2
    report = analyze_similarity(gen_text, ref_texts, "proj_1")
    save_similarity_report(str(tmp_path), report, 1)
    
    report_file = tmp_path / "chapter_1_similarity_report.json"
    content = report_file.read_text(encoding='utf-8')
    assert "极度机密" not in content
    
    data = json.loads(content)
    assert data["needs_rewrite"] is True
    assert "reasons" in data
    assert "rewrite_instruction" not in data # original prompt rewrite instruction shouldn't be in saved report

def test_generation_pipeline_rewrite_trigger(test_workspace, monkeypatch):
    project_id, filepath = test_workspace
    
    # Mock bindings to enable guard
    def mock_get_bindings(pid):
        return [{"enabled": True, "use_anti_copy_guard": True, "book_id": "book1"}]
    def mock_build_reference_context(pid):
        return {"book1": {"data": {"style_bible": "我是原文" * 20}}}
        
    import backend.app.services.local_reference_context_service as lrcs
    import novel_generator.chapter
    import novel_generator.chapter_pipeline.revision
    import novel_generator.chapter_pipeline.quality_checker
    
    monkeypatch.setattr(lrcs, "get_bindings", mock_get_bindings)
    monkeypatch.setattr(lrcs, "build_reference_context", mock_build_reference_context)
    monkeypatch.setattr(novel_generator.chapter, "create_llm_adapter", lambda *args, **kwargs: llm)
    monkeypatch.setattr(novel_generator.chapter_pipeline.revision, "create_specialized_chat_adapter", lambda *args, **kwargs: llm)
    monkeypatch.setattr(novel_generator.chapter_pipeline.quality_checker, "create_specialized_chat_adapter", lambda *args, **kwargs: llm)
    
    llm = DummyLLM([
        "我是原文" * 20, # First draft is too similar
        "我是原文" * 20, # First rewrite is still too similar
        "我是原创的文本，没有任何问题，完全不一样的内容，测试测试" # Second rewrite is ok
    ])
    ctx = DummyContext(project_id, filepath, llm)
    
    # Need to touch some dummy files for prompt builder
    for f in ["Novel_architecture.txt", "Novel_directory.txt", "core_summary.txt"]:
        with open(os.path.join(filepath, f), 'w', encoding='utf-8') as fh:
            fh.write("")
            
    chapter_content = generate_chapter_draft(ctx, DummyParams())
    
    assert "完全不一样" in chapter_content
    assert llm.call_count > 3 # Draft + Voice + Eval + (maybe Quality Rewrite) + Similarity Rewrite

def test_generation_pipeline_rewrite_max_limit(test_workspace, monkeypatch):
    project_id, filepath = test_workspace
    
    def mock_get_bindings(pid):
        return [{"enabled": True, "use_anti_copy_guard": True, "book_id": "book1"}]
    def mock_build_reference_context(pid):
        return {"book1": {"data": {"style_bible": "永远不变的原文" * 20}}}
        
    import backend.app.services.local_reference_context_service as lrcs
    import novel_generator.chapter
    import novel_generator.chapter_pipeline.revision
    import novel_generator.chapter_pipeline.quality_checker
    
    monkeypatch.setattr(lrcs, "get_bindings", mock_get_bindings)
    monkeypatch.setattr(lrcs, "build_reference_context", mock_build_reference_context)
    
    # LLM always returns similar text
    llm = DummyLLM(["永远不变的原文" * 20] * 10)
    
    monkeypatch.setattr(novel_generator.chapter, "create_llm_adapter", lambda *args, **kwargs: llm)
    monkeypatch.setattr(novel_generator.chapter_pipeline.revision, "create_specialized_chat_adapter", lambda *args, **kwargs: llm)
    monkeypatch.setattr(novel_generator.chapter_pipeline.quality_checker, "create_specialized_chat_adapter", lambda *args, **kwargs: llm)
    
    ctx = DummyContext(project_id, filepath, llm)
    
    for f in ["Novel_architecture.txt", "Novel_directory.txt", "core_summary.txt"]:
        with open(os.path.join(filepath, f), 'w', encoding='utf-8') as fh:
            fh.write("")
            
    chapter_content = generate_chapter_draft(ctx, DummyParams())
    
    assert llm.call_count > 3
    assert "永远不变的原文" in chapter_content
