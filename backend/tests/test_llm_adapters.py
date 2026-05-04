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


if __name__ == "__main__":
    unittest.main()
