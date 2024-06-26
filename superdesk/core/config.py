# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, Optional, TypeVar, Type, Union

from pydantic import BaseModel, ConfigDict


class ConfigModel(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    _loaded: bool = False

    def __eq__(self, other: Any) -> bool:
        # We only support checking config instances vs other config instances
        return False if not isinstance(other, ConfigModel) else self.__dict__ == other.__dict__

    def __getattribute__(self, name: str):
        # Allow unrestricted access to private and pydantic private attributes
        if name.startswith("_") or name.startswith("model_"):
            return BaseModel.__getattribute__(self, name)

        if not self._loaded:
            raise RuntimeError(f"Config {self.__class__} not loaded, while accessing attribute '{name}'")

        return BaseModel.__getattribute__(self, name)


ConfigClassType = TypeVar("ConfigClassType", bound=ConfigModel)


def get_config_key(key: str, prefix: Optional[str] = None) -> str:
    """Get a config key with optional prefix"""

    return f"{prefix.upper()}_{key.upper()}" if prefix else key.upper()


def _get_config_dict(
    app_config: Dict[str, Any],
    config_class: Union[Type[ConfigClassType], ConfigClassType],
    prefix: Optional[str] = None,
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}

    for field_name, field_info in config_class.model_fields.items():
        config_name = get_config_key(field_name, prefix)
        if config_name in app_config:
            kwargs[field_name] = app_config[config_name]
        else:
            kwargs[field_name] = field_info.default

    return kwargs


def get_config_instance(
    app_config: Dict[str, Any],
    config_class: Type[ConfigClassType],
    prefix: Optional[str] = None,
    freeze: bool = True,
) -> ConfigClassType:
    """Construct a new config instance, populating values from ``app_config``"""

    config_instance = config_class.model_validate(_get_config_dict(app_config, config_class, prefix))
    if freeze:
        config_instance.model_config["frozen"] = True
    config_instance._loaded = True
    return config_instance


def load_config_instance(
    app_config: Dict[str, Any], config_instance: ConfigClassType, prefix: Optional[str] = None, freeze: bool = True
) -> ConfigClassType:
    """Reload config instance values, populating them from ``app_config``

    This will load a brand-new instance of the config, applying values from ``app_config`` on top of the
    class' default values. This means any custom changes made before calling this will be lost.
    """

    # If the ``config_instance`` is currently frozen, temporarily un-freeze it, so we can update it
    # and then freeze it again after updating the values
    if config_instance.model_config.get("frozen", False):
        # freeze = True
        config_instance.model_config["frozen"] = False

    for key, val in _get_config_dict(app_config, config_instance, prefix).items():
        setattr(config_instance, key, val)

    config_instance.model_config["frozen"] = freeze
    config_instance._loaded = True

    return config_instance
