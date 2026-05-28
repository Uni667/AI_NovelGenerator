"""章节管理路由集成测试。"""
import os
import shutil
import pytest
from backend.app.database import get_connection

@pytest.fixture
def test_chapter(test_project):
    # Insert a dummy chapter in SQLite database
    conn = get_connection()
    conn.execute(
        """INSERT INTO chapter (user_id, project_id, chapter_number, chapter_title, chapter_role, chapter_purpose,
           suspense_level, foreshadowing, plot_twist_level, chapter_summary, word_count, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (test_project["user_id"], test_project["id"], 1, "第1章 开始", "铺垫", "引入危机",
         "中", "埋线索", "★☆☆☆☆", "主角开局醒来", 12, "draft", "2026-05-28T00:00:00", "2026-05-28T00:00:00")
    )
    conn.commit()
    conn.close()
    
    # Create the physical chapter file
    filepath = test_project["filepath"]
    os.makedirs(os.path.join(filepath, "chapters"), exist_ok=True)
    with open(os.path.join(filepath, "chapters", "chapter_1.txt"), "w", encoding="utf-8") as f:
        f.write("这是测试正文内容。")
        
    yield {
        "project_id": test_project["id"],
        "chapter_number": 1,
        "chapter_title": "第1章 开始",
        "filepath": filepath
    }
    
    # Cleanup physical files
    if os.path.exists(filepath):
        shutil.rmtree(filepath, ignore_errors=True)


class TestChapterRoutes:
    def test_update_chapter_meta(self, client, auth_headers, test_chapter):
        """测试更新章节的元数据（标题、定位、作用等）。"""
        update_data = {
            "chapter_title": "修改后的章节标题",
            "chapter_role": "高潮",
            "chapter_purpose": "正面冲突",
            "suspense_level": "强",
            "foreshadowing": "回收伏笔",
            "plot_twist_level": "★★★☆☆",
            "chapter_summary": "主角正面迎敌，发现真相"
        }
        url = f"/api/v1/projects/{test_chapter['project_id']}/chapters/{test_chapter['chapter_number']}"
        response = client.put(url, json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "已保存"
        assert data["meta"]["chapter_title"] == "修改后的章节标题"
        assert data["meta"]["chapter_role"] == "高潮"
        assert data["meta"]["chapter_purpose"] == "正面冲突"
        assert data["meta"]["suspense_level"] == "强"
        assert data["meta"]["foreshadowing"] == "回收伏笔"
        assert data["meta"]["plot_twist_level"] == "★★★☆☆"
        assert data["meta"]["chapter_summary"] == "主角正面迎敌，发现真相"

    def test_copy_chapter(self, client, auth_headers, test_chapter):
        """测试复制/克隆章节功能。"""
        url = f"/api/v1/projects/{test_chapter['project_id']}/chapters/{test_chapter['chapter_number']}/copy"
        response = client.post(url, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "复制成功"
        assert data["meta"]["chapter_number"] == 2
        assert data["meta"]["chapter_title"] == "第1章 开始 - 副本"
        assert data["meta"]["chapter_role"] == "铺垫"
        assert data["meta"]["chapter_purpose"] == "引入危机"
        assert data["meta"]["word_count"] == 12
        assert data["meta"]["status"] == "draft"
        
        # 验证物理文件是否也被成功拷贝
        dst_file = os.path.join(test_chapter["filepath"], "chapters", "chapter_2.txt")
        assert os.path.exists(dst_file)
        with open(dst_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == "这是测试正文内容。"
