from typing import Optional, Dict, Any
from superdesk.core.module import Module
from superdesk.core.config import ConfigModel


class ModuleConfig(ConfigModel):
    default_string: str = "test-default"
    optional_string: Optional[str] = None
    any_dict: Optional[Dict[str, Any]] = None
    int_dict: Optional[Dict[str, int]] = None
    custom_int: Optional[int] = None


config = ModuleConfig()


module = Module(name="tests.module_with_config", config=config)
