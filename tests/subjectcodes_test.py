import unittest

from superdesk.flask import Flask
from superdesk.io.subjectcodes import init_app


class SubjectsTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_app_subjects(self):
        app = Flask(__name__)
        app.api_prefix = "/test"
        init_app(app)
        async with app.app_context():
            app.subjects.register({"01000000": "Foo"})
            self.assertEqual("Foo", app.subjects["01000000"])
            app.subjects.clear()
            with self.assertRaises(KeyError):
                app.subjects["01000000"]
