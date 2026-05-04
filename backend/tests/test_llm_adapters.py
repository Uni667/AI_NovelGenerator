import unittest
from unittest.mock import patch

import httpx

import llm_adapters
from novel_generator.cancel_token import CancelToken


class _DummyTransport(httpx.BaseTransport):
    def handle_request(self, request):
        return httpx.Response(200, request=request, content=b"ok")

    def close(self):
        return None


class CancelClientTests(unittest.TestCase):
    def test_make_cancel_client_wraps_response_stream_as_sync_stream(self):
        llm_adapters._httpx = httpx
        with patch.object(llm_adapters._httpx, "HTTPTransport", _DummyTransport):
            client = llm_adapters._make_cancel_client(CancelToken(), 5.0)
            try:
                response = client.get("https://example.com")
            finally:
                client.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "ok")


class ApiCredentialServiceTests(unittest.TestCase):
    """测试 API 凭证服务的参数映射和校验逻辑。"""

    def test_provider_defaults_are_urls_not_model_names(self):
        """PROVIDER_DEFAULTS 只应该被用作 base_url，不能当 model_name。"""
        from backend.app.services.api_credential_service import PROVIDER_DEFAULTS

        for provider, value in PROVIDER_DEFAULTS.items():
            if not value:
                continue
            self.assertTrue(
                value.startswith("http://") or value.startswith("https://"),
                f"PROVIDER_DEFAULTS['{provider}'] = {value!r} 应该是 URL",
            )

    def test_provider_test_models_are_not_urls(self):
        """PROVIDER_DEFAULT_TEST_MODELS 必须是模型名，不能是 URL。"""
        from backend.app.services.api_credential_service import PROVIDER_DEFAULT_TEST_MODELS

        for provider, value in PROVIDER_DEFAULT_TEST_MODELS.items():
            if not value:
                continue
            self.assertFalse(
                value.startswith("http://") or value.startswith("https://"),
                f"PROVIDER_DEFAULT_TEST_MODELS['{provider}'] = {value!r} 不能是 URL，这是模型名",
            )

    def test_validate_model_not_url_rejects_http(self):
        """_validate_model_not_url 拒绝 http:// 开头的字符串。"""
        from backend.app.services.api_credential_service import _validate_model_not_url

        with self.assertRaises(ValueError) as ctx:
            _validate_model_not_url("https://api.deepseek.com")
        self.assertIn("base_url", str(ctx.exception))
        self.assertIn("model", str(ctx.exception))

    def test_validate_model_not_url_accepts_normal_name(self):
        """_validate_model_not_url 接受普通模型名。"""
        from backend.app.services.api_credential_service import _validate_model_not_url

        # 正常模型名不抛异常
        _validate_model_not_url("deepseek-v4-flash")
        _validate_model_not_url("gpt-4o-mini")
        _validate_model_not_url("qwen-plus")
        _validate_model_not_url("")  # 空字符串也不抛

    def test_test_chat_uses_model_not_base_url(self):
        """_test_chat 传给 create_llm_adapter 的 model_name 必须是模型名，不是 base_url。"""
        from unittest.mock import patch
        from backend.app.services.api_credential_service import _test_chat, PROVIDER_DEFAULTS

        cred = {
            "id": "test-cred-id",
            "provider": "deepseek",
            "base_url": "",
            "api_key_encrypted": "dummy-encrypted-key",
        }

        # create_llm_adapter 是在 _test_chat 内部通过 from llm_adapters import 引入的，
        # 所以要 mock llm_adapters.create_llm_adapter
        with patch("backend.app.services.api_credential_service.decrypt_api_key", return_value="sk-test-key"):
            with patch("llm_adapters.create_llm_adapter") as mock_adapter:
                mock_adapter.return_value.invoke.return_value = "OK"
                _test_chat(cred, "sk-test-key")

        call_kwargs = mock_adapter.call_args.kwargs
        model_name = call_kwargs["model_name"]
        base_url = call_kwargs["base_url"]

        # base_url 应该是 DeepSeek API 地址
        self.assertEqual(base_url, PROVIDER_DEFAULTS["deepseek"],
                         f"base_url={base_url!r} 应该是 DeepSeek API 地址")
        # model_name 绝对不能是 URL
        self.assertFalse(
            model_name.startswith("http://") or model_name.startswith("https://"),
            f"model_name={model_name!r} 不应该是 URL！",
        )
        self.assertEqual(model_name, "deepseek-chat",
                         f"model_name 应该是 deepseek-chat，实际是 {model_name!r}")


if __name__ == "__main__":
    unittest.main()
