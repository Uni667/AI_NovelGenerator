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

    def test_get_stream_token_success(self, client, auth_headers, test_user):
        """成功获取短期 stream token并进行验证。"""
        response = client.post("/api/v1/auth/stream-token", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "stream_token" in data
        
        stream_token = data["stream_token"]
        from backend.app.auth import verify_stream_token, verify_access_token
        
        # 1. verify_stream_token 应该成功解析该 stream token
        payload = verify_stream_token(stream_token)
        assert payload["user_id"] == test_user["id"]
        assert payload["type"] == "stream"
        assert payload["aud"] == "sse"
        
        # 2. verify_access_token 应该拒绝该 stream token
        with pytest.raises(Exception):
            verify_access_token(stream_token)

    def test_get_stream_token_unauthorized(self, client):
        """无 token 请求 stream-token 接口返回 401。"""
        response = client.post("/api/v1/auth/stream-token")
        assert response.status_code == 401

    def test_verify_stream_token_rejects_access_token(self, auth_token):
        """verify_stream_token 应该拒绝标准的 access token。"""
        from backend.app.auth import verify_stream_token
        with pytest.raises(Exception):
            verify_stream_token(auth_token)

    def test_sse_endpoint_rejects_access_token_in_url(self, client, auth_token):
        """SSE 风格的 URL 参数传入 access token 时应该被拒绝。"""
        response = client.get("/api/v1/auth/me", params={"token": auth_token})
        assert response.status_code == 401

    def test_sse_endpoint_accepts_stream_token_in_url(self, client, auth_headers):
        """SSE 风格的 URL 参数传入 stream token 应成功通过 get_current_user 鉴权。"""
        response = client.post("/api/v1/auth/stream-token", headers=auth_headers)
        assert response.status_code == 200
        stream_token = response.json()["stream_token"]
        
        response2 = client.get("/api/v1/auth/me", params={"token": stream_token})
        assert response2.status_code == 200
        assert response2.json()["username"] == "testuser"

