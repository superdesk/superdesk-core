import flask
import unittest


from superdesk.io.subjectcodes import init_app


class SubjectsTestCase(unittest.TestCase):
    def test_app_subjects(self):
        app = flask.Flask(__name__)
        app.api_prefix = "/test"
        init_app(app)
        with app.app_context():
            app.subjects.register({"01000000": "Foo"})
            self.assertEqual("Foo", app.subjects["01000000"])
            app.subjects.clear()
            with self.assertRaises(KeyError):
                app.subjects["01000000"]
