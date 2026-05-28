import pytest
import os
from novel_generator.chapter import generate_chapter_draft
from novel_generator.finalization import finalize_chapter
from novel_generator.context import ChapterParams

class MockEmitter:
    def __init__(self):
        self.events = []
    def emit(self, event_type, data):
        self.events.append((event_type, data))

def test_generate_chapter_draft(mock_llm_adapter, mock_generation_context, test_project_dir):
    params = ChapterParams(chapter_number=1, word_number=2000)
    emitter = MockEmitter()
    
    # Test full generation
    draft_content = generate_chapter_draft(
        ctx=mock_generation_context,
        params=params,
        custom_prompt_text="Test prompt",
        emitter=emitter,
        start_step=None
    )
    
    assert "This is a generated chapter draft" in draft_content
    # Check if partial file was cleaned up
    assert not os.path.exists(os.path.join(test_project_dir, "chapters", "chapter_1_partial.txt"))
    # Check if final file is created
    assert os.path.exists(os.path.join(test_project_dir, "chapters", "chapter_1.txt"))
    
    # Check emitter events
    event_steps = [e[1]["step"] for e in emitter.events]
    assert "drafting" in event_steps
    assert "voice_polish" in event_steps

def test_resume_chapter_generation(mock_llm_adapter, mock_generation_context, test_project_dir):
    params = ChapterParams(chapter_number=2, word_number=2000)
    emitter = MockEmitter()
    
    # Create a partial file manually to simulate a break at voice_polish
    partial_file = os.path.join(test_project_dir, "chapters", "chapter_2_partial.txt")
    with open(partial_file, "w", encoding="utf-8") as f:
        f.write("Draft content from previous step")
        
    draft_content = generate_chapter_draft(
        ctx=mock_generation_context,
        params=params,
        custom_prompt_text="Test prompt",
        emitter=emitter,
        start_step="quality_check"
    )
    
    # Check emitter events to ensure it skipped drafting and voice_polish
    event_steps = [e[1]["step"] for e in emitter.events]
    assert "drafting" not in event_steps
    assert "voice_polish" not in event_steps
    assert "quality_check" in event_steps

def test_finalize_chapter_with_compression(mock_llm_adapter, mock_generation_context, test_project_dir):
    params = ChapterParams(chapter_number=1, word_number=2000)
    
    # Create a long global summary to trigger compression
    long_summary = "A" * 2000
    global_summary_file = os.path.join(test_project_dir, "global_summary.txt")
    with open(global_summary_file, "w", encoding="utf-8") as f:
        f.write(long_summary)
        
    chapter_file = os.path.join(test_project_dir, "chapters", "chapter_1.txt")
    with open(chapter_file, "w", encoding="utf-8") as f:
        f.write("Some chapter text")
        
    finalize_chapter(ctx=mock_generation_context, params=params)
    
    # Check if summary was compressed
    with open(global_summary_file, "r", encoding="utf-8") as f:
        new_summary = f.read()
    
    assert "This is a compressed summary" in new_summary


def test_run_multi_agent_brainstorming(mock_llm_adapter, mock_generation_context):
    from novel_generator.chapter_pipeline.brainstorm import run_multi_agent_brainstorming
    emitter = MockEmitter()
    chapter_info = {
        "chapter_number": 3,
        "chapter_title": "Test Chapter",
        "chapter_role": "Conflict Escalation",
        "chapter_purpose": "Make protagonist struggle",
        "chapter_summary": "Protagonist fights a mock beast."
    }
    
    guidance = run_multi_agent_brainstorming(
        ctx=mock_generation_context,
        global_summary="Initial global summary",
        chapter_info=chapter_info,
        emitter=emitter
    )
    
    assert "多智能体头脑风暴-高燃突发事件指南" in guidance
    assert len(emitter.events) == 6 # 3 agents running + 3 agents done = 6 progress events
    steps = [e[1]["step"] for e in emitter.events]
    assert "brainstorm_reader" in steps
    assert "brainstorm_villain" in steps
    assert "brainstorm_director" in steps


def test_sliding_context_generation(mock_llm_adapter, mock_generation_context, test_project_dir):
    from novel_generator.chapter_pipeline.prompt_builder import build_chapter_prompt
    from novel_generator.context import ChapterParams
    
    # 1. 模拟存在之前的章节正文
    chapters_dir = os.path.join(test_project_dir, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)
    
    # 创建第 1 章正文
    with open(os.path.join(chapters_dir, "chapter_1.txt"), "w", encoding="utf-8") as f:
        f.write("这是第一章的全文正文内容。主角登场，觉醒了金手指。")
        
    # 创建第 2 章正文
    with open(os.path.join(chapters_dir, "chapter_2.txt"), "w", encoding="utf-8") as f:
        f.write("这是第二章的全文正文内容。主角离开新手村，踏上征途。")
        
    # 2. 我们生成第 3 章的提示词
    params = ChapterParams(chapter_number=3, word_number=2000)
    prompt = build_chapter_prompt(mock_generation_context, params)
    
    # 3. 验证结果
    # 应该生成了摘要缓存文件 chapter_1_summary.txt
    summary_file_1 = os.path.join(chapters_dir, "chapter_1_summary.txt")
    assert os.path.exists(summary_file_1)
    with open(summary_file_1, "r", encoding="utf-8") as f:
        summary_content = f.read()
    assert "This is a single chapter summary" in summary_content
    
    assert "第 1 章剧情摘要" in prompt
    assert "This is a single chapter summary" in prompt
    assert "这是第二章的全文正文内容。主角离开新手村，踏上征途。" in prompt


def test_quality_checker_no_slice_for_reasonable_length(mock_llm_adapter, mock_generation_context):
    from novel_generator.chapter_pipeline.quality_checker import analyze_chapter_quality
    import unittest.mock as mock
    
    mock_llm_adapter.invoke = mock.MagicMock(return_value='{"opening":{"score":9,"issues":[],"suggestion":""}}')
    
    text_under_limit = "测试内容\n" * 100
    with mock.patch("novel_generator.chapter_pipeline.quality_checker.get_semantic_segments") as mock_slice:
        analyze_chapter_quality(mock_generation_context, text_under_limit)
        mock_slice.assert_not_called()
        
    text_over_limit = "测试超长内容，做切片质检测试测试超长内容，做切片质检测试\n" * 250
    with mock.patch("novel_generator.chapter_pipeline.quality_checker.get_semantic_segments") as mock_slice:
        mock_slice.return_value = "sliced text"
        analyze_chapter_quality(mock_generation_context, text_over_limit)
        mock_slice.assert_called_once()

