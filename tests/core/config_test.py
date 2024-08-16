import unittest

from pydantic import ValidationError

from superdesk.tests import AsyncTestCase
from .modules import module_with_config


class ConfigTestCase(unittest.TestCase):
    def test_restricted_access_to_config_if_not_loaded(self):
        config = module_with_config.ModuleConfig()
        with self.assertRaises(RuntimeError):
            self.assertEqual(config.default_string, "test-default")
        config.load_from_dict({"DEFAULT_STRING": "test-loaded-values"})
        self.assertEqual(config.default_string, "test-loaded-values")

        new_config = module_with_config.ModuleConfig.create_from_dict({})
        self.assertEqual(new_config.default_string, "test-default")

    def test_default_values(self):
        # Test default values
        self.assertEqual(
            module_with_config.ModuleConfig.create_from_dict({}),
            module_with_config.ModuleConfig(),
        )
        self.assertEqual(
            module_with_config.ModuleConfig.create_from_dict({}),
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
            module_with_config.ModuleConfig.create_from_dict({"CUSTOM_DEFAULT_STRING": "test-modified"}, "CUSTOM"),
            module_with_config.ModuleConfig(default_string="test-modified"),
        )

        # Test keys must use capital letters
        self.assertEqual(
            module_with_config.ModuleConfig.create_from_dict({"default_string": "modified-value"}),
            module_with_config.ModuleConfig(default_string="test-default"),
        )
        self.assertEqual(
            module_with_config.ModuleConfig.create_from_dict({"DEFAULT_STRING": "test-modified-2"}),
            module_with_config.ModuleConfig(default_string="test-modified-2"),
        )

    def test_config_validation(self):
        # Providing str instead of int
        with self.assertRaises(ValidationError):
            module_with_config.ModuleConfig.create_from_dict({"CUSTOM_INT": "val"})

        # Incorrect dict type
        with self.assertRaises(ValidationError):
            module_with_config.ModuleConfig.create_from_dict({"INT_DICT": {"key1": True, "key2": "val", "key3": 23}})

        # Test dict with ``Any`` value
        module_with_config.ModuleConfig.create_from_dict({"ANY_DICT": {"key1": True, "key2": "val", "key3": 23}})


class ModuleConfigTestCase(AsyncTestCase):
    app_config = {"MODULES": ["tests.core.modules.module_with_config"]}
    autorun = False

    async def asyncSetUp(self, force: bool = False):
        self.app_config = {"MODULES": ["tests.core.modules.module_with_config"]}
        module_with_config.config.load_from_dict({}, freeze=False)
        module_with_config.module.config_prefix = None
        module_with_config.module.freeze_config = True
        await super().asyncSetUp()

    def test_module_config(self):
        self.setupApp()
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
