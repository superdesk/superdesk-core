import pytest
from unittest.mock import patch, MagicMock

from superdesk.auth.utils import generate_url_with_token


class TestGenerateUrlWithToken:
    def test_simple_url(self):
        with patch("superdesk.utils.jwt_encode") as mock_encode:
            mock_encode.return_value = "test_token"
            result = generate_url_with_token("/api/download/123", media_id="123")
            assert result == "/api/download/123?token=test_token"
            mock_encode.assert_called_once_with({"media_id": "123"}, expiry=7)

    def test_url_with_existing_query_params(self):
        with patch("superdesk.utils.jwt_encode") as mock_encode:
            mock_encode.return_value = "test_token"
            result = generate_url_with_token("/api/download/123?foo=bar", media_id="123")
            assert result == "/api/download/123?foo=bar&token=test_token"

    def test_custom_expiry(self):
        with patch("superdesk.utils.jwt_encode") as mock_encode:
            mock_encode.return_value = "test_token"
            generate_url_with_token("/api/download/123", expiry_days=30, media_id="123")
            mock_encode.assert_called_once_with({"media_id": "123"}, expiry=30)

    def test_multiple_payload_params(self):
        with patch("superdesk.utils.jwt_encode") as mock_encode:
            mock_encode.return_value = "test_token"
            generate_url_with_token("/api/download/123", media_id="123", user_id="456")
            mock_encode.assert_called_once_with({"media_id": "123", "user_id": "456"}, expiry=7)

    def test_full_url(self):
        with patch("superdesk.utils.jwt_encode") as mock_encode:
            mock_encode.return_value = "test_token"
            result = generate_url_with_token(
                "https://api.example.com/download/123?existing=param",
                media_id="123",
            )
            assert result == "https://api.example.com/download/123?existing=param&token=test_token"
