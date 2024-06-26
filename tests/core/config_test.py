import unittest
from dataclasses import dataclass

from pydantic import ValidationError

from superdesk.core.config import get_config_instance, load_config_instance

from superdesk.tests.asyncio import AsyncTestCase
from .modules import module_with_config


class ConfigTestCase(unittest.TestCase):
    def test_default_values(self):
        # Test default values
        self.assertEqual(
            get_config_instance({}, module_with_config.ModuleConfig),
            module_with_config.ModuleConfig(),
        )
        self.assertEqual(
            get_config_instance({}, module_with_config.ModuleConfig),
            module_with_config.ModuleConfig(
                default_string="test-default",
                optional_string=None,
                any_dict=None,
                int_dict=None,
                custom_int=None,
            ),
        )

    def test_key_name_format(self):
        # Test default values with prefix
        self.assertEqual(
            get_config_instance({"CUSTOM_DEFAULT_STRING": "test-modified"}, module_with_config.ModuleConfig, "CUSTOM"),
            module_with_config.ModuleConfig(default_string="test-modified"),
        )

        # Test keys must use capital letters
        self.assertEqual(
            get_config_instance({"default_string": "modified-value"}, module_with_config.ModuleConfig),
            module_with_config.ModuleConfig(default_string="test-default"),
        )
        self.assertEqual(
            get_config_instance({"DEFAULT_STRING": "test-modified-2"}, module_with_config.ModuleConfig),
            module_with_config.ModuleConfig(default_string="test-modified-2"),
        )

    def test_config_validation(self):
        # Providing str instead of int
        with self.assertRaises(ValidationError):
            get_config_instance({"CUSTOM_INT": "val"}, module_with_config.ModuleConfig)

        # Incorrect dict type
        with self.assertRaises(ValidationError):
            get_config_instance(
                {"INT_DICT": {"key1": True, "key2": "val", "key3": 23}},
                module_with_config.ModuleConfig,
            )

        # Test dict with ``Any`` value
        get_config_instance(
            {"ANY_DICT": {"key1": True, "key2": "val", "key3": 23}},
            module_with_config.ModuleConfig,
        )

        # Invalid config class type
        @dataclass
        class DataConfig:
            name: str = "test-name"

        with self.assertRaises(AttributeError):
            get_config_instance({}, DataConfig)


class ModuleConfigTestCase(AsyncTestCase):
    app_config = {"MODULES": ["tests.core.modules.module_with_config"]}
    autorun = False

    async def asyncSetUp(self, force: bool = False):
        self.app_config = {"MODULES": ["tests.core.modules.module_with_config"]}
        load_config_instance({}, module_with_config.config, freeze=False)
        module_with_config.module.config_prefix = None
        module_with_config.module.freeze_config = True
        await super().asyncSetUp()

    def test_module_config(self):
        print(self.app_config)
        self.setupApp()
        print(module_with_config.ModuleConfig())
        print(module_with_config.config)
        self.assertEqual(module_with_config.ModuleConfig(), module_with_config.config)

    def test_app_fails_to_start_with_invalid_config(self):
        self.app_config["DEFAULT_STRING"] = "abcd123"
        self.setupApp()
        self.assertEqual(module_with_config.config.default_string, "abcd123")

    def test_module_config_prefix(self):
        module_with_config.module.config_prefix = "CUSTOM"
        self.app_config["CUSTOM_DEFAULT_STRING"] = "abcd123"
        self.setupApp()
        self.assertEqual(module_with_config.config.default_string, "abcd123")

    def test_module_config_immutability(self):
        self.setupApp()

        # Test module config immutability
        with self.assertRaises(ValidationError):
            module_with_config.config.default_string = "test-immutability"
        self.assertEqual(module_with_config.config.default_string, "test-default")

    def test_module_config_mutable(self):
        module_with_config.module.freeze_config = False
        self.setupApp()

        # Test module config is mutable
        module_with_config.config.default_string = "test-immutability"
        self.assertEqual(module_with_config.config.default_string, "test-immutability")
