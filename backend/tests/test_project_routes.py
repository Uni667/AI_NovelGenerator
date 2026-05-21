"""项目管理路由集成测试。"""
import pytest
from unittest.mock import patch


class TestProjectRoutes:
    """测试项目管理相关 API。"""

    def test_list_projects_empty(self, client, auth_headers):
        """用户无项目时返回空列表。"""
        response = client.get("/api/v1/projects", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_projects_with_data(self, client, auth_headers, test_project):
        """用户有项目时返回列表。"""
        response = client.get("/api/v1/projects", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(p["id"] == test_project["id"] for p in data)

    def test_create_project(self, client, auth_headers, test_user_id):
        """成功创建项目。"""
        project_data = {
            "name": "新项目",
            "description": "测试项目描述",
            "topic": "测试主题",
            "genre": "奇幻",
            "num_chapters": 10,
            "word_number": 3000,
            "language": "zh",
            "platform": "tomato"
        }
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "新项目"
        assert data["user_id"] == test_user_id

    def test_create_project_missing_name(self, client, auth_headers):
        """创建项目缺少名称应返回 422。"""
        response = client.post("/api/v1/projects", json={
            "description": "无名称项目"
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_get_project(self, client, auth_headers, test_project):
        """获取项目详情。"""
        response = client.get(f"/api/v1/projects/{test_project['id']}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_project["id"]
        assert data["name"] == "测试项目"

    def test_get_project_not_found(self, client, auth_headers):
        """获取不存在的项目应返回 404。"""
        response = client.get("/api/v1/projects/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_update_project(self, client, auth_headers, test_project):
        """更新项目信息。"""
        response = client.put(
            f"/api/v1/projects/{test_project['id']}",
            json={"name": "更新后的项目名", "description": "更新描述"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新后的项目名"

    def test_update_project_not_found(self, client, auth_headers):
        """更新不存在的项目应返回 404。"""
        response = client.put(
            "/api/v1/projects/nonexistent-id",
            json={"name": "更新"},
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_delete_project(self, client, auth_headers, test_project):
        """删除项目。"""
        response = client.delete(f"/api/v1/projects/{test_project['id']}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

        # 验证项目已删除
        response = client.get(f"/api/v1/projects/{test_project['id']}", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_project_not_found(self, client, auth_headers):
        """删除不存在的项目应返回 404。"""
        response = client.delete("/api/v1/projects/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_get_project_config(self, client, auth_headers, test_project):
        """获取项目配置。"""
        response = client.get(f"/api/v1/projects/{test_project['id']}/config", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == "测试主题"
        assert data["genre"] == "奇幻"

    def test_update_project_config(self, client, auth_headers, test_project):
        """更新项目配置。"""
        response = client.put(
            f"/api/v1/projects/{test_project['id']}/config",
            json={"topic": "新主题", "genre": "科幻", "num_chapters": 20},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == "新主题"
        assert data["genre"] == "科幻"
        assert data["num_chapters"] == 20

    def test_unauthorized_access(self, client):
        """无认证访问项目 API 应返回 401。"""
        response = client.get("/api/v1/projects")
        assert response.status_code == 401

    def test_project_isolation(self, client, auth_headers, test_user_id, test_project):
        """用户只能看到自己的项目。"""
        # 创建另一个用户的项目
        import uuid
        from datetime import datetime, timezone
        from backend.app.database import get_connection

        other_user_id = str(uuid.uuid4())
        other_project_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        conn = get_connection()
        conn.execute(
            "INSERT INTO user (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (other_user_id, "otheruser", "hashed", now)
        )
        conn.execute(
            "INSERT INTO project (id, user_id, name, description, filepath, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (other_project_id, other_user_id, "其他用户项目", "", f"/tmp/other_{other_project_id}", "draft", now, now)
        )
        conn.commit()
        conn.close()

        # 当前用户不应看到其他用户的项目
        response = client.get("/api/v1/projects", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert not any(p["id"] == other_project_id for p in data)
