# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import TypeVar, cast
from typing_extensions import Self
from importlib import import_module
from datetime import datetime
from uuid import uuid4

from .app import get_app_config

GUID_TAG = "tag"
GUID_NEWSML = "newsml"


def generate_guid(**hints) -> str:
    """Generate a GUID based on given hints

    param: hints: hints used for generating the guid
    """
    newsml_guid_format = "urn:newsml:%(domain)s:%(timestamp)s:%(identifier)s"
    tag_guid_format = "tag:%(domain)s:%(year)d:%(identifier)s"

    if not hints.get("id"):
        hints["id"] = str(uuid4())

    def get_conf(key: str, default: bool | str) -> bool | str:
        try:
            return cast(bool | str, get_app_config(key, default))
        except RuntimeError:
            return default

    try:
        if get_conf("GENERATE_SHORT_GUID", False):
            return hints["id"]
    except RuntimeError:
        # This occurs when attempting to generate an ID when app isn't running
        # No need to bail out, just continue on assuming GENERATE_SHORT_GUID is False
        pass

    t = datetime.today()

    if hints["type"].lower() == GUID_TAG:
        return tag_guid_format % {
            "domain": get_conf("URN_DOMAIN", "localhost"),
            "year": t.year,
            "identifier": hints["id"],
        }

    return newsml_guid_format % {
        "domain": get_conf("URN_DOMAIN", "localhost"),
        "timestamp": t.isoformat(),
        "identifier": hints["id"],
    }


def str_to_date(value: str | datetime | None) -> datetime | None:
    """Convert a string to a datetime instance"""

    if isinstance(value, str):
        date_format: str = get_app_config("DATE_FORMAT") or "%Y-%m-%dT%H:%M:%S+0000"
        return datetime.strptime(value, date_format)

    return value


def date_to_str(value: datetime | None) -> str | None:
    """Convert a datetime instance to a string"""

    date_format: str = get_app_config("DATE_FORMAT") or "%Y-%m-%dT%H:%M:%S+0000"
    return datetime.strftime(value, date_format) if value else None


MODULE_CLASS_TYPE = TypeVar("MODULE_CLASS_TYPE")


def load_class_from_config(class_type: type[MODULE_CLASS_TYPE], config_key: str) -> type[MODULE_CLASS_TYPE]:
    """
    Load a class from configuration.

    This function retrieves a class definition from the given configuration key by
    parsing its module path and attribute. The module is imported dynamically, and
    the required class is validated against the expected base class type provided.

    Raises an exception if the configuration value is invalid, the module or
    attribute cannot be found, or if the class does not match the expected type.

    :param class_type: The expected base class type that the loaded class must inherit from.
    :param config_key: The key used to retrieve the configuration value that defines the module and class.
    :return: The dynamically imported class that matches the expected type.
    :raises RuntimeError: If the configuration value is invalid, the module or attribute cannot
        be retrieved, or the loaded class does not match the required base type.
    """

    config_str = cast(str, get_app_config(config_key))
    try:
        module_path, module_attribute = config_str.split(":", 1)
    except ValueError as error:
        raise RuntimeError(f"Invalid config {config_key}={config_str}: {error}")

    imported_module = import_module(module_path)
    module_class = getattr(imported_module, module_attribute)

    if not issubclass(module_class, class_type):
        raise RuntimeError(f"Invalid config {config_key}={config_str}, invalid class type {module_class}")

    return cast(type[MODULE_CLASS_TYPE], module_class)


class SingletonInstance(object):
    """
    A base class implementing the Singleton design pattern.

    This class serves as a base class for creating singleton instances. Any class
    that inherits from this will enforce a single instance of itself. Direct
    instantiation of SingletonInstance itself is prohibited. Instead, it is
    intended to be subclassed with logic for handling singleton-specific
    initialization.

    Attributes:
        __instance: Class-level attribute used to store the unique instance of the
        subclass. Initialized as None if not already set.

    """

    @classmethod
    def _get_instance(cls) -> Self | None:
        return getattr(cls, "__instance", None)

    @classmethod
    def _set_instance(cls, instance: Self) -> None:
        setattr(cls, "__instance", instance)

    def _init_instance(self, *args, **kwargs) -> None:
        pass

    def __new__(cls, *args, **kwargs):
        if cls == SingletonInstance:
            raise RuntimeError("SingletonInstance cannot be used directly")

        instance = cls._get_instance()
        if not instance:
            instance = super(SingletonInstance, cls).__new__(cls, *args, **kwargs)
            instance._init_instance(*args, **kwargs)
            cls._set_instance(instance)

        return instance
