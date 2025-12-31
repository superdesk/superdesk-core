import pytest
from superdesk.lookup_validation import validate_lookup_for_sensitive_fields
from superdesk.errors import SuperdeskApiError


class TestLookupValidation:
    def test_simple_sensitive_field(self):
        """Test that direct filtering on sensitive field is blocked"""
        with pytest.raises(SuperdeskApiError) as exc_info:
            validate_lookup_for_sensitive_fields({"password": "test"}, ["password"])
        assert "Filtering by password is not allowed" in str(exc_info.value)

    def test_nested_sensitive_field(self):
        """Test that filtering on nested sensitive field is blocked"""
        with pytest.raises(SuperdeskApiError) as exc_info:
            validate_lookup_for_sensitive_fields({"config.password": "test"}, ["config"])
        assert "Filtering by config is not allowed" in str(exc_info.value)

    def test_regex_on_sensitive_field(self):
        """Test that regex filtering on sensitive field is blocked"""
        with pytest.raises(SuperdeskApiError) as exc_info:
            validate_lookup_for_sensitive_fields({"password": {"$regex": "^secret"}}, ["password"])
        assert "Filtering by password is not allowed" in str(exc_info.value)

    def test_or_with_sensitive_field(self):
        """Test that $or containing sensitive field is blocked"""
        with pytest.raises(SuperdeskApiError) as exc_info:
            validate_lookup_for_sensitive_fields(
                {"$or": [{"password": {"$regex": "^test"}}, {"username": "admin"}]}, ["password"]
            )
        assert "Filtering by password is not allowed" in str(exc_info.value)

    def test_and_with_sensitive_field(self):
        """Test that $and containing sensitive field is blocked"""
        with pytest.raises(SuperdeskApiError) as exc_info:
            validate_lookup_for_sensitive_fields(
                {"$and": [{"name": "test"}, {"password": {"$regex": "^secret"}}]}, ["password"]
            )
        assert "Filtering by password is not allowed" in str(exc_info.value)

    def test_nested_or_and_with_sensitive_field(self):
        """Test that nested $or/$and containing sensitive field is blocked"""
        with pytest.raises(SuperdeskApiError) as exc_info:
            validate_lookup_for_sensitive_fields(
                {"$or": [{"$and": [{"name": "test"}, {"token": "value"}]}, {"username": "admin"}]}, ["token"]
            )
        assert "Filtering by token is not allowed" in str(exc_info.value)

    def test_nor_with_sensitive_field(self):
        """Test that $nor containing sensitive field is blocked"""
        with pytest.raises(SuperdeskApiError) as exc_info:
            validate_lookup_for_sensitive_fields({"$nor": [{"password": "test"}]}, ["password"])
        assert "Filtering by password is not allowed" in str(exc_info.value)

    def test_not_operator_with_sensitive_field(self):
        """Test that $not containing sensitive field is blocked"""
        with pytest.raises(SuperdeskApiError) as exc_info:
            validate_lookup_for_sensitive_fields({"password": {"$not": {"$regex": "^test"}}}, ["password"])
        assert "Filtering by password is not allowed" in str(exc_info.value)

    def test_nested_config_with_regex(self):
        """Test that nested config fields with regex are blocked"""
        with pytest.raises(SuperdeskApiError) as exc_info:
            validate_lookup_for_sensitive_fields(
                {"destinations.config.password": {"$regex": "^Super"}}, ["destinations.config"]
            )
        assert "Filtering by destinations.config is not allowed" in str(exc_info.value)

    def test_allowed_fields_with_operators(self):
        """Test that non-sensitive fields with operators are allowed"""
        # Should not raise any exception
        validate_lookup_for_sensitive_fields(
            {"$or": [{"username": {"$regex": "^test"}}, {"email": {"$regex": "@example.com"}}]}, ["password"]
        )

    def test_allowed_nested_fields(self):
        """Test that non-sensitive nested fields are allowed"""
        # Should not raise any exception
        validate_lookup_for_sensitive_fields({"config.url": "http://example.com"}, ["destinations.config"])

    def test_empty_sensitive_fields(self):
        """Test that empty sensitive fields list allows all queries"""
        # Should not raise any exception
        validate_lookup_for_sensitive_fields({"password": {"$regex": "^test"}}, [])

    def test_none_lookup(self):
        """Test that None lookup is handled gracefully"""
        # Should not raise any exception
        validate_lookup_for_sensitive_fields(None, ["password"])

    def test_multiple_sensitive_fields(self):
        """Test blocking multiple different sensitive fields"""
        with pytest.raises(SuperdeskApiError) as exc_info:
            validate_lookup_for_sensitive_fields({"token": "value"}, ["password", "token", "secret"])
        assert "Filtering by token is not allowed" in str(exc_info.value)

        with pytest.raises(SuperdeskApiError) as exc_info:
            validate_lookup_for_sensitive_fields({"secret": "value"}, ["password", "token", "secret"])
        assert "Filtering by secret is not allowed" in str(exc_info.value)
