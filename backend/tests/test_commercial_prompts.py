"""单元测试：商业化提示词构建。"""
import pytest
from novel_generator.commercial_prompts import (
    SUPPORTED_MODES,
    CommercialPromptInput,
    safety_prompt,
    system_prompt,
    story_context_prompt,
    output_format_prompt,
    chapter_diagnosis_dimensions,
    build_commercial_prompt,
    build_generation_context_block,
)


class TestSafetyPrompt:
    """测试安全提示词。"""

    def test_contains_author_boundaries(self):
        """包含作者控制边界声明。"""
        result = safety_prompt()
        assert "不写真实人物谣言" in result
        assert "世界观" in result or "设定" in result
        assert "用户输入为准" in result

    def test_contains_content_rules(self):
        """包含内容安全规则。"""
        result = safety_prompt()
        assert "仇恨" in result or "色情" in result
        assert "照搬现实新闻" in result


class TestSystemPrompt:
    """测试系统角色提示词。"""

    def test_defines_role(self):
        """定义了 AI 角色。"""
        result = system_prompt()
        assert "主编" in result
        assert "商业化编辑" in result
        assert "读者画像分析师" in result

    def test_contains_task_rule(self):
        """包含任务规则。"""
        result = system_prompt()
        assert "冲突" in result
        assert "理念" in result


class TestStoryContextPrompt:
    """测试故事上下文提示词。"""

    def test_includes_all_fields(self):
        """包含所有用户可控参数。"""
        data = CommercialPromptInput(novel_name="测试", forbidden="不变")
        result = story_context_prompt(data)
        assert "小说名称" in result
        assert "测试" in result
        assert "不变" in result

    def test_empty_fields_show_unspecified(self):
        """空字段显示为未指定。"""
        data = CommercialPromptInput()
        result = story_context_prompt(data)
        assert result.count("未指定") >= 5


class TestOutputFormatPrompt:
    """测试输出格式提示词。"""

    def test_diagnose_mode(self):
        """诊断模式输出格式。"""
        result = output_format_prompt("diagnose")
        assert "总体评分" in result
        assert "平台适配" in result
        assert "改写示范" in result

    def test_platform_rewrite_mode(self):
        """平台改写模式输出格式。"""
        result = output_format_prompt("platform_rewrite")
        assert "原章节问题" in result
        assert "改写后正文" in result

    def test_short_drama_mode(self):
        """短剧模式输出格式。"""
        result = output_format_prompt("short_drama")
        assert "分镜式大纲" in result
        assert "爆点台词" in result

    def test_default_mode(self):
        """默认/章节生成模式输出格式。"""
        result = output_format_prompt("generate_chapter")
        assert "本章标题" in result
        assert "本章爽点" in result
        assert "结尾钩子" in result

    def test_unknown_mode_falls_back(self):
        """未知模式回退到默认格式。"""
        result = output_format_prompt("nonexistent_mode")
        assert "本章标题" in result


class TestDiagnosisDimensions:
    """测试诊断维度。"""

    def test_contains_all_dimensions(self):
        """包含15个评分维度。"""
        result = chapter_diagnosis_dimensions("tomato")
        assert "平台适配度" in result
        assert "开篇钩子" in result
        assert "女主主体性" in result
        assert "反派压迫感" in result
        assert "追读钩子" in result
        assert "空泛哲理" in result
        assert "节奏拖慢" in result

    def test_includes_platform_specific_focus(self):
        """包含平台特定关注点。"""
        result = chapter_diagnosis_dimensions("tomato")
        assert "平台额外关注" in result


class TestBuildCommercialPrompt:
    """测试完整商业提示词构建。"""

    def test_diagnose_mode_contains_diagnosis(self):
        """诊断模式包含诊断维度。"""
        data = CommercialPromptInput(mode="diagnose", platform="tomato")
        result = build_commercial_prompt(data)
        assert "总体评分" in result
        assert "诊断维度" in result

    def test_all_modes_contain_safety(self):
        """所有模式都包含安全提示。"""
        for mode in ["generate_chapter", "diagnose", "rewrite_chapter", "platform_rewrite"]:
            data = CommercialPromptInput(mode=mode, platform="tomato")
            result = build_commercial_prompt(data)
            assert "不写真实人物谣言" in result, f"{mode} 缺少安全提示"

    def test_contains_platform_info(self):
        """包含平台信息。"""
        data = CommercialPromptInput(mode="generate_chapter", platform="qidian")
        result = build_commercial_prompt(data)
        assert "起点" in result

    def test_trend_included_when_set(self):
        """热点转译被包含。"""
        data = CommercialPromptInput(mode="generate_chapter", platform="tomato", trend_key="fairness_anxiety")
        result = build_commercial_prompt(data)
        assert "公平焦虑" in result

    def test_forbidden_fields_preserved(self):
        """禁止改动设定被保留。"""
        data = CommercialPromptInput(forbidden="不可改变主角性别")
        result = build_commercial_prompt(data)
        assert "不可改变主角性别" in result

    def test_empty_input_does_not_crash(self):
        """空输入不崩溃。"""
        data = CommercialPromptInput()
        result = build_commercial_prompt(data)
        assert len(result) > 100  # 至少有基本的提示词文本

    def test_all_modes_generate_non_empty(self):
        """所有模式都生成非空提示词。"""
        for mode in SUPPORTED_MODES:
            data = CommercialPromptInput(mode=mode, platform="tomato", chapter_text="测试章节内容")
            result = build_commercial_prompt(data)
            assert len(result) > 50, f"{mode} 提示词为空"


class TestBuildGenerationContextBlock:
    """测试生成上下文块。"""

    def test_contains_platform_and_safety(self):
        """包含平台约束和安全规则。"""
        result = build_generation_context_block(platform="fanqie_free")
        assert "平台化网文创作约束" in result
        assert "安全与作者控制边界" in result

    def test_trend_in_context(self):
        """热点在上下文块中显示。"""
        result = build_generation_context_block(
            platform="tomato", trend_key="labor_discipline"
        )
        assert "打工人" in result

    def test_forbidden_in_context(self):
        """禁止设定在上下文块中显示。"""
        result = build_generation_context_block(
            platform="tomato", forbidden="禁止修改主线"
        )
        assert "禁止修改主线" in result

    def test_empty_readership_shows_default(self):
        """未指定读者方向时显示默认。"""
        result = build_generation_context_block(platform="tomato")
        assert "默认读者画像" in result


class TestSupportedModes:
    """测试支持的创作模式。"""

    def test_all_modes_have_labels(self):
        """所有模式都有标签。"""
        assert len(SUPPORTED_MODES) >= 12
        for key, label in SUPPORTED_MODES.items():
            assert isinstance(label, str)
            assert len(label) > 0

    def test_key_modes_exist(self):
        """核心模式都存在。"""
        expected = {
            "generate_chapter", "rewrite_chapter", "diagnose",
            "outline", "platform_rewrite", "short_drama",
            "selling_points", "ending_hook", "set_piece",
            "platform_opening", "character_bio", "volume_outline",
        }
        assert expected.issubset(set(SUPPORTED_MODES.keys()))
