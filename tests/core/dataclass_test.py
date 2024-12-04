from unittest import TestCase

from pydantic_core import ValidationError
from superdesk.core.resources import Dataclass


class RingBearer(Dataclass):
    name: str
    race: str


class DataclassTest(TestCase):
    def test_dataclass_model_proper_types(self):
        frodo = RingBearer(name="Frodo", race="Hobbit")
        frodo_from_dict = RingBearer.from_dict(dict(name="Frodo", race="Hobbit"))
        frodo_from_json = RingBearer.from_json('{"name":"Frodo","race":"Hobbit"}')

        self.assertEqual(type(frodo), RingBearer)
        self.assertEqual(type(frodo_from_dict), RingBearer)
        self.assertEqual(type(frodo_from_json), RingBearer)

    def test_dataclass_model_utils(self):
        frodo = RingBearer(name="Frodo", race="Hobbit")

        self.assertEqual(frodo.to_dict(), {"name": "Frodo", "race": "Hobbit"})
        self.assertEqual(frodo.to_json(), '{"name":"Frodo","race":"Hobbit"}')

    def test_dataclass_validation_error(self):
        with self.assertRaises(ValidationError, msg="1 validation error for RingBearer"):
            RingBearer(name="Frodo")

        with self.assertRaises(ValidationError):
            RingBearer(name=1, race="Hobbit")

    def test_dataclass_should_validate_on_assignment(self):
        with self.assertRaises(ValidationError):
            frodo = RingBearer(name="Frodo", race="Hobbit")
            frodo.name = 1
