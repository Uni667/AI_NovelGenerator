import unittest

from novel_generator.character_import import build_character_import_preview


class CharacterImportTests(unittest.TestCase):
    def test_preview_keeps_real_character_and_rejects_place_noise(self):
        state_text = """
# 人物规划

## 李明
- 身份：主角
- 目标：查明真相
- 首次登场：第3章

## 北京
- 地点：北方城市
- 作用：开场事件发生地
"""

        preview = build_character_import_preview(state_text, [])
        by_name = {item.name: item for item in preview}

        self.assertIn("李明", by_name)
        self.assertNotEqual(by_name["李明"].decision, "reject")
        self.assertEqual(by_name["李明"].first_appearance_chapter, 3)

        self.assertIn("北京", by_name)
        self.assertNotEqual(by_name["北京"].entity_type, "character")
        self.assertEqual(by_name["北京"].decision, "reject")

    def test_preview_merges_duplicate_character_blocks(self):
        state_text = """
# 角色状态

## 林澈
- 身份：主角
- 目标：寻找失踪的妹妹

## 林澈
- 关系：与反派有旧怨
- 秘密：隐瞒真实能力
"""

        preview = build_character_import_preview(state_text, [])
        matches = [item for item in preview if item.name == "林澈"]

        self.assertEqual(len(matches), 1)
        self.assertIn("寻找失踪的妹妹", matches[0].description)
        self.assertIn("隐瞒真实能力", matches[0].description)


if __name__ == "__main__":
    unittest.main()
