# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Privileges registry."""
from typing import Optional
from .errors import PrivilegeNameError
from flask_babel.speaklater import LazyString

import superdesk

_privileges = {}
_intrinsic_privileges = {}


GLOBAL_SEARCH_PRIVILEGE = "use_global_saved_searches"


def privilege(
    name,
    label: Optional[LazyString] = None,
    description: Optional[LazyString] = None,
    category: Optional[LazyString] = None,
    **kwargs,
):
    """Register privilege.

    Privilege name must not contain "."

    Privilege properties:
    - name
    - label
    - description
    - category
    """
    if "." in name:
        raise PrivilegeNameError('"." is not supported in privilege name "%s"' % name)
    _privileges[name] = kwargs
    _privileges[name].update(
        dict(
            name=name,
            label=label,
            category=category,
            description=description,
        )
    )


def get_item_privilege_name(resource: str, item):
    return "resource:{}:{}".format(resource, item["_id"])


def _get_resource_privileges():
    resource_privileges = []
    for name, resource in superdesk.resources.items():
        if not getattr(resource, "item_privileges", None):
            continue
        items = superdesk.get_resource_service(name).get(None, {})
        for item in items:
            try:
                label = resource.item_privileges_label.format(**item)
            except KeyError:
                label = "{}: {}".format(name, item["_id"])
            resource_privileges.append(
                {
                    "name": get_item_privilege_name(name, item),
                    "label": label,
                    "category": name,
                }
            )
    return resource_privileges


def _get_registered_privileges():
    """Get list of all registered privileges."""
    return [v for v in _privileges.values()]


def get_privilege_list():
    return _get_registered_privileges() + _get_resource_privileges()


def intrinsic_privilege(resource_name, method=None):
    """
    Registers intrinsic privileges.
    """

    if method is None:
        method = []

    _intrinsic_privileges[resource_name] = method


def get_intrinsic_privileges():
    """Get list of all registered intrinsic privileges."""

    return _intrinsic_privileges
