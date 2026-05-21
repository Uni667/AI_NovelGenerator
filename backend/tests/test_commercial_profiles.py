"""单元测试：平台画像和热点转译。"""
import pytest
from novel_generator.commercial_profiles import (
    DEFAULT_PLATFORM_KEY,
    PLATFORM_ALIASES,
    PLATFORM_PROFILES,
    TREND_TRANSLATORS,
    normalize_platform_key,
    get_platform_profile,
    get_trend_translation,
    format_profile_for_prompt,
    format_trend_for_prompt,
    list_platform_profiles,
    list_trend_translators,
)


class TestPlatformProfiles:
    """测试平台画像数据结构和读取。"""

    def test_all_profiles_loaded(self):
        """所有平台画像都定义且结构完整。"""
        assert len(PLATFORM_PROFILES) >= 4
        required_keys = {"readerPreference", "chapterRequirement", "avoid", "hookStrategy", "diagnosisFocus"}
        for key, profile in PLATFORM_PROFILES.items():
            for rk in required_keys:
                assert rk in profile, f"{key} 缺少 {rk}"
            assert profile.get("name"), f"{key} 缺少 name"

    def test_default_platform_is_valid(self):
        """默认平台必须在画像字典中。"""
        assert DEFAULT_PLATFORM_KEY in PLATFORM_PROFILES

    def test_normalize_known_aliases(self):
        """已知别名映射到正确画像。"""
        assert normalize_platform_key("tomato") == "fanqie_free"
        assert normalize_platform_key("qidian") == "qidian_male"
        assert normalize_platform_key("jjwxc") == "jjwxc_xianxia"
        assert normalize_platform_key("short") == "short_drama"
        assert normalize_platform_key("drama") == "short_drama"

    def test_normalize_unknown_returns_default(self):
        """未识别平台返回默认画像。"""
        assert normalize_platform_key("madeup") == DEFAULT_PLATFORM_KEY
        assert normalize_platform_key("") == DEFAULT_PLATFORM_KEY
        assert normalize_platform_key(None) == DEFAULT_PLATFORM_KEY

    def test_normalize_case_insensitive(self):
        """大小写不敏感。"""
        assert normalize_platform_key("QiDian") == "qidian_male"

    def test_get_platform_profile_includes_key(self):
        """返回的 profile 包含 key 字段。"""
        profile = get_platform_profile("tomato")
        assert profile["key"] == "fanqie_free"
        assert profile["name"] == "番茄 / 七猫免费阅读"

    def test_get_platform_profile_all_platforms(self):
        """所有平台都能获取 profile。"""
        for key in PLATFORM_PROFILES:
            profile = get_platform_profile(key)
            assert "readerPreference" in profile
            assert "avoid" in profile
            assert "hookStrategy" in profile

    def test_list_platform_profiles_is_copy(self):
        """list_platform_profiles 返回深拷贝，修改不影响原数据。"""
        profiles = list_platform_profiles()
        profiles["test"] = {"name": "test"}
        assert "test" not in PLATFORM_PROFILES

    def test_format_profile_for_prompt_contains_key_info(self):
        """format 输出包含平台关键信息。"""
        result = format_profile_for_prompt("tomato")
        assert "番茄" in result
        assert "读者偏好" in result
        assert "章节要求" in result
        assert "需要避免" in result
        assert "追读钩子策略" in result


class TestTrendTranslators:
    """测试热点转译数据结构和使用。"""

    def test_all_trends_loaded(self):
        """所有转译规则都定义完整。"""
        assert len(TREND_TRANSLATORS) >= 7
        required_keys = {"name", "realEmotion", "fictionalTranslation", "avoid"}
        for key, trend in TREND_TRANSLATORS.items():
            for rk in required_keys:
                assert rk in trend, f"{key} 缺少 {rk}"
            assert len(trend["fictionalTranslation"]) >= 3, f"{key} 虚构转译数量不足"

    def test_get_trend_valid(self):
        """获取有效热点转译。"""
        trend = get_trend_translation("resource_anxiety")
        assert trend is not None
        assert trend["name"] == "资源焦虑"
        assert len(trend["fictionalTranslation"]) >= 3

    def test_get_trend_none(self):
        """空或无效输入返回 None。"""
        assert get_trend_translation(None) is None
        assert get_trend_translation("") is None
        assert get_trend_translation("nonexistent") is None

    def test_get_trend_is_copy(self):
        """返回深拷贝。"""
        trend = get_trend_translation("resource_anxiety")
        trend["fictionalTranslation"].append("test")
        original = TREND_TRANSLATORS["resource_anxiety"]
        assert "test" not in original["fictionalTranslation"]

    def test_format_trend_with_valid_key(self):
        """有效热点生成完整提示文本。"""
        result = format_trend_for_prompt("resource_anxiety")
        assert "资源焦虑" in result
        assert "现实情绪抽象" in result
        assert "小说化转译备选" in result
        assert "禁止" in result

    def test_format_trend_none_key(self):
        """无热点时给出默认说明。"""
        result = format_trend_for_prompt(None)
        assert "未指定" in result
        assert "普遍情绪" in result

    def test_format_trend_with_custom(self):
        """自定义热点正确拼接。"""
        result = format_trend_for_prompt(None, custom_trend="测试情绪")
        assert "测试情绪" in result
        assert "不得照搬真实新闻" in result

    def test_format_trend_with_both(self):
        """既有预设又有自定义时两者都包含。"""
        result = format_trend_for_prompt("fairness_anxiety", custom_trend="自定义")
        assert "公平焦虑" in result
        assert "自定义" in result

    def test_list_trend_translators_is_copy(self):
        """返回深拷贝。"""
        trends = list_trend_translators()
        trends["test"] = {}
        assert "test" not in TREND_TRANSLATORS

    def test_all_trends_have_avoid_rules(self):
        """每条转译规则都包含禁止事项。"""
        for key, trend in TREND_TRANSLATORS.items():
            assert len(trend["avoid"]) >= 1, f"{key} 缺少禁止事项"
