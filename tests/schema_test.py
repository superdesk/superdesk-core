import unittest

from superdesk.schema import Schema, StringField, IntegerField, ListField, DictField, SchemaField, NoneField


class TestSchema(Schema):

    string_field = StringField()

    integer_field = IntegerField()

    list_field = ListField()

    dict_field = DictField()

    empty_field = SchemaField()

    none_field = NoneField()


class SchemaTest(unittest.TestCase):
    def test_schema_iterable(self):
        schema = dict(TestSchema)
        self.assertIn("string_field", schema)
        self.assertEqual(
            schema["string_field"], {"type": "string", "required": False, "minlength": None, "maxlength": None}
        )
        self.assertEqual(schema["integer_field"], {"type": "integer", "required": False})
        self.assertEqual(
            schema["list_field"], {"type": "list", "required": False, "mandatory_in_list": None, "schema": None}
        )
        self.assertEqual(schema["dict_field"], {"type": "dict", "required": False})
        self.assertEqual(schema["empty_field"], {})
        self.assertEqual(None, schema["none_field"])
