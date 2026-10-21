from unittest import IsolatedAsyncioTestCase, TestCase, mock

from superdesk.core.app import SuperdeskAsyncApp, get_app_config
from superdesk.core.privileges import Privilege
from superdesk.flask import Flask
from superdesk.tests import AsyncQuartTestCase, MockWSGI


class AsyncQuartAppIsolationTestCase(AsyncQuartTestCase):
    app_config = {"CONFIG_VALUE": "context"}

    async def asyncSetUp(self):
        self.global_wsgi = MockWSGI(config={"CONFIG_VALUE": "global"})
        self.global_app = SuperdeskAsyncApp(self.global_wsgi)
        global_patch = mock.patch("superdesk.core.app._global_app", self.global_app)
        global_patch.start()
        self.addCleanup(global_patch.stop)
        await super().asyncSetUp()

    async def test_local_context_does_not_replace_global_wsgi(self):
        self.assertIs(self.global_app.wsgi, self.global_wsgi)
        self.assertEqual(get_app_config("CONFIG_VALUE"), "context")


class AppConfigTestCase(IsolatedAsyncioTestCase):
    async def test_active_context_takes_precedence_over_global_app(self):
        app = Flask(__name__)
        app.config["CONFIG_VALUE"] = "context"
        global_app = SuperdeskAsyncApp(MockWSGI(config={"CONFIG_VALUE": "global", "GLOBAL_ONLY": "global"}))
        with mock.patch("superdesk.core.app._global_app", global_app):
            async with app.app_context():
                self.assertEqual(get_app_config("CONFIG_VALUE"), "context")
                self.assertEqual(get_app_config("GLOBAL_ONLY", "default"), "default")
                self.assertIsNone(get_app_config("GLOBAL_ONLY"))
            self.assertEqual(get_app_config("CONFIG_VALUE"), "global")
            self.assertEqual(get_app_config("MISSING", "default"), "default")

    async def test_active_context_without_global_app(self):
        app = Flask(__name__)
        app.config["CONFIG_VALUE"] = "context"
        with mock.patch("superdesk.core.app._global_app", None):
            async with app.app_context():
                self.assertEqual(get_app_config("CONFIG_VALUE"), "context")
                self.assertEqual(get_app_config("MISSING", "default"), "default")

    async def test_no_app_raises(self):
        with mock.patch("superdesk.core.app._global_app", None):
            with self.assertRaisesRegex(RuntimeError, "Superdesk app is not running"):
                get_app_config("CONFIG_VALUE")


class SuperdeskAsyncAppTestCase(TestCase):
    def test_construction(self):
        # Test starting the app, and the ``running`` property
        app = SuperdeskAsyncApp(MockWSGI(config={}))
        self.assertFalse(app.running)
        app.start()
        self.assertTrue(app.running)

        # Test exception raised if attempting to start an already running app
        with self.assertRaises(RuntimeError):
            app.start()

    def test_loading_modules(self):
        # Test module loading, and populating of the path attribute
        config = {"MODULES": ["tests.core.modules.a", "tests.core.modules.b"]}
        app = SuperdeskAsyncApp(MockWSGI(config=config))
        app.start()
        self.assertEqual(len(app._imported_modules), 2)
        self.assertEqual(app._imported_modules["tests.module_a"].path, "tests.core.modules.a")
        self.assertEqual(app._imported_modules["tests.module_b"].path, "tests.core.modules.b")

        # Test overriding a module
        config["MODULES"] = ["tests.core.modules.a", "tests.core.modules.a2"]
        app = SuperdeskAsyncApp(MockWSGI(config=config))
        app.start()
        self.assertEqual(app._imported_modules["tests.module_a"].path, "tests.core.modules.a2")

        # Test frozen modules cannot be overridden
        config["MODULES"] = ["tests.core.modules.b", "tests.core.modules.b2_invalid"]
        with self.assertRaises(RuntimeError):
            SuperdeskAsyncApp(MockWSGI(config=config)).start()

        # Test loading all modules, and sorting by priority
        config["MODULES"] = ["tests.core.modules.a", "tests.core.modules.b", "tests.core.modules.a2"]
        app = SuperdeskAsyncApp(MockWSGI(config=config))
        app.start()
        modules = app.get_module_list()
        self.assertEqual(len(modules), 2)
        self.assertEqual([m.name for m in modules], ["tests.module_b", "tests.module_a"])

    def test_invalid_modules(self):
        with self.assertRaises(RuntimeError):
            SuperdeskAsyncApp(MockWSGI(config={"MODULES": ["tests.core.modules.c_invalid"]})).start()

        with self.assertRaises(RuntimeError):
            SuperdeskAsyncApp(MockWSGI(config={"MODULES": ["tests.core.modules.d_invalid"]})).start()

    @mock.patch("tests.core.modules.a.module.init")
    def test_module_init(self, init):
        app = SuperdeskAsyncApp(MockWSGI(config={"MODULES": ["tests.core.modules.a"]}))
        app.start()
        init.assert_called_once_with(app)

    def test_register_privileges(self):
        app = SuperdeskAsyncApp(MockWSGI(config={"MODULES": ["tests.core.modules.module_with_privileges"]}))
        app.start()

        # check privileges are registered
        registered_privileges = app.privileges.get_all()
        self.assertEqual(len(registered_privileges), 2)
        self.assertTrue(app.privileges.is_locked)

        # after app is started, trying to register a privilege raise an exception
        with self.assertRaises(RuntimeError) as exc:
            app.privileges.add(Privilege(name="After app started"))
            self.assertEqual(exc.msg, "Cannot add privileges after the app has started")
