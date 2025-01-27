from typing import Any, cast

from quart_babel import gettext
from superdesk.errors import SuperdeskApiError
from superdesk.users.async_service import get_privileges, is_admin
from superdesk.core.types import HTTP_METHOD, AuthRule, Request


def required_privilege_rule(privilege: str) -> AuthRule:
    """
    Creates an authentication rule that restricts access based on a specific privilege.

    Args:
        privilege (str): The privilege required to access the resource.

    Returns:
        AuthRule: An asynchronous rule function that checks if the user has the required privilege.

    The rule verifies:
    - If the user is an admin, access is granted without further checks.
    - Otherwise, the user's privileges are retrieved and checked against the required privilege.

    Raises:
        SuperdeskApiError: If the user does not have the required privilege.
    """

    async def internal_rule(request: Request):
        current_user = request.user

        # TODO-ASYNC: Check if for admin we need to pull all privileges instead
        if is_admin(current_user):
            return None

        user_role = request.storage.request.get("role")
        user_privileges = get_privileges(request.user, user_role)

        if user_privileges.get(privilege, False):
            return None

        raise SuperdeskApiError.forbiddenError(message=gettext("Insufficient privileges for the requested operation."))

    return internal_rule


def privilege_based_rules(rules: dict[HTTP_METHOD, str]) -> dict[str, AuthRule]:
    """
    Generates a dictionary of authentication rules for HTTP methods based on privileges.

    Args:
        rules (dict[HTTP_METHOD, str]): A mapping of HTTP methods (e.g., GET, POST) to the required privileges
        for those methods.

    Returns:
        dict[str, list[AuthRule]]: A dictionary where each HTTP method is mapped to a list of authentication
        rules that restrict access based on the specified privilege.
    """

    auth_rules: dict[str, AuthRule] = {}
    for method, privilege_name in rules.items():
        auth_rules[method] = required_privilege_rule(privilege_name)

    return auth_rules
