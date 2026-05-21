"""认证路由集成测试。"""
import pytest
from unittest.mock import patch


class TestAuthRoutes:
    """测试认证相关 API。"""

    def test_register_success(self, client):
        """成功注册用户。"""
        response = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "password": "password123"
        })
        # 注册成功应返回 200 或用户信息
        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data or "token" in data

    def test_register_duplicate_username(self, client, test_user):
        """注册重复用户名应返回 400。"""
        response = client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "password123"
        })
        assert response.status_code == 400

    def test_register_short_username(self, client):
        """用户名太短应返回 422。"""
        response = client.post("/api/v1/auth/register", json={
            "username": "a",
            "password": "password123"
        })
        assert response.status_code == 422

    def test_register_short_password(self, client):
        """密码太短应返回 422。"""
        response = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "password": "123"
        })
        assert response.status_code == 422

    def test_login_success(self, client, test_user):
        """成功登录。"""
        # 由于测试用户使用的是哈希密码，需要 mock 验证
        with patch("backend.app.services.user_service.verify_password", return_value=True):
            response = client.post("/api/v1/auth/login", json={
                "username": "testuser",
                "password": "password123"
            })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data or "access_token" in data

    def test_login_wrong_password(self, client, test_user):
        """密码错误应返回 401。"""
        with patch("backend.app.services.user_service.verify_password", return_value=False):
            response = client.post("/api/v1/auth/login", json={
                "username": "testuser",
                "password": "wrongpassword"
            })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """不存在的用户应返回 401。"""
        response = client.post("/api/v1/auth/login", json={
            "username": "nonexistent",
            "password": "password123"
        })
        assert response.status_code == 401

    def test_me_with_valid_token(self, client, auth_headers, test_user):
        """有效 token 获取当前用户信息。"""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    def test_me_without_token(self, client):
        """无 token 访问受保护端点应返回 401。"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_with_invalid_token(self, client):
        """无效 token 应返回 401。"""
        response = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert response.status_code == 401
