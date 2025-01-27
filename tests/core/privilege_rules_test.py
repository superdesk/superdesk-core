import pytest
from unittest.mock import patch, MagicMock
from superdesk.errors import SuperdeskApiError
from superdesk.core.auth.privilege_rules import privilege_based_rules, required_privilege_rule


@patch("superdesk.core.auth.privilege_rules.is_admin")
@patch("superdesk.core.auth.privilege_rules.get_privileges")
async def test_required_privilege_rule_admin(mock_get_privileges, mock_is_admin):
    mock_is_admin.return_value = True
    mock_request = MagicMock()

    rule = required_privilege_rule("test_privilege")
    result = await rule(mock_request)

    # admin user should pass without checking privileges
    assert result is None
    mock_get_privileges.assert_not_called()


@patch("superdesk.core.auth.privilege_rules.is_admin")
@patch("superdesk.core.auth.privilege_rules.get_privileges")
async def test_required_privilege_rule_insufficient_privileges(mock_get_privileges, mock_is_admin):
    mock_is_admin.return_value = False
    mock_get_privileges.return_value = {"test_privilege": False}

    mock_request = MagicMock()
    mock_request.user = "test_user"
    mock_request.storage.request.get.return_value = "user_role"

    rule = required_privilege_rule("test_privilege")

    with pytest.raises(SuperdeskApiError) as error:
        await rule(mock_request)

    assert error.value.status_code == 403
    assert "Insufficient privileges" in str(error.value)
    mock_get_privileges.assert_called_once_with("test_user", "user_role")


@patch("superdesk.core.auth.privilege_rules.is_admin")
@patch("superdesk.core.auth.privilege_rules.get_privileges")
async def test_required_privilege_rule_sufficient_privileges(mock_get_privileges, mock_is_admin):
    mock_is_admin.return_value = False
    mock_get_privileges.return_value = {"test_privilege": True}

    mock_request = MagicMock()
    mock_request.user = "test_user"
    mock_request.storage.request.get.return_value = "user_role"

    rule = required_privilege_rule("test_privilege")

    result = await rule(mock_request)
    assert result is None
    mock_get_privileges.assert_called_once_with("test_user", "user_role")


def test_privilege_based_rules():
    rules = {
        "GET": "read_articles",
        "POST": "create_articles",
        "DELETE": "delete_articles",
    }

    auth_rules = privilege_based_rules(rules)

    assert "GET" in auth_rules
    assert "POST" in auth_rules
    assert "DELETE" in auth_rules
