import os
import flask
import unittest


class TestConfig:
    X = True


class ConfigTestCase(unittest.TestCase):
    def test_config_update(self):
        config = flask.Config(os.path.abspath(os.path.dirname(__file__)))
        config.update({"X": True})
        self.assertTrue(config.get("X"))
        config.update({"X": False})
        self.assertFalse(config.get("X"))
        config.from_object(TestConfig())
        self.assertTrue(config.get("X"))
