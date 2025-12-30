# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Utilities for validating lookup queries against sensitive fields."""

from typing import Any, List
from superdesk.errors import SuperdeskApiError


def validate_lookup_for_sensitive_fields(lookup: dict | list | None, sensitive_fields: List[str]) -> None:
    """Validate that a lookup query does not attempt to filter by sensitive fields.

    This prevents NoSQL injection attacks where attackers could use regex or other
    operators to guess values of sensitive fields like passwords, tokens, etc.

    :param lookup: The lookup dictionary or list to validate
    :param sensitive_fields: List of field names that should not be allowed in filters
    :raises SuperdeskApiError.badRequestError: If lookup attempts to filter by a sensitive field
    """
    if not lookup or not sensitive_fields:
        return

    _validate_lookup_recursive(lookup, sensitive_fields)


def _validate_lookup_recursive(lookup: Any, sensitive_fields: List[str]) -> None:
    """Recursively validate lookup structure for sensitive field access.

    :param lookup: Current lookup node (dict, list, or other value)
    :param sensitive_fields: List of field names that should not be allowed
    :raises SuperdeskApiError.badRequestError: If a sensitive field is found
    """
    if isinstance(lookup, dict):
        for key, value in lookup.items():
            # Check if the key itself is a sensitive field
            if key in sensitive_fields:
                raise SuperdeskApiError.badRequestError(f"Filtering by {key} is not allowed")

            # Check if the key is a nested path under a sensitive field (e.g., "config.password")
            for sensitive in sensitive_fields:
                if key.startswith(f"{sensitive}."):
                    raise SuperdeskApiError.badRequestError(f"Filtering by {sensitive} is not allowed")

            # Recursively validate the value
            _validate_lookup_recursive(value, sensitive_fields)
    elif isinstance(lookup, list):
        for item in lookup:
            _validate_lookup_recursive(item, sensitive_fields)
