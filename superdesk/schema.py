__all__ = (
    "Schema",
    "NoneField",
    "SchemaField",
    "StringField",
    "IntegerField",
    "ListField",
    "DictField",
    "RelatedContentField",
)


class SchemaType(type):
    """Type for schema.

    It makes Schema class iterable, so you can get the schema dict
    for it using ``dict(Schema)``.
    """

    def __iter__(self):
        for k in dir(self):
            if isinstance(getattr(self, k), SchemaField):
                yield (k, getattr(self, k).schema)


class Schema(metaclass=SchemaType):
    """Base class for schema definition.

    This allows you to define schema as a class with attributes,
    which makes it easier for documentation than normal dictionary.
    """

    pass


class SchemaField:
    """Schema field.

    These are for defining Schema class attributes.
    """

    def __repr__(self):
        return "any"

    def __init__(self):
        self.schema = {}


class NoneField(SchemaField):
    """None field."""

    def __repr__(self):
        return "none"

    def __init__(self):
        self.schema = None


class IntegerField(SchemaField):
    """Integer schema field."""

    def __repr__(self):
        return "integer"

    def __init__(self, required=False):
        super().__init__()
        self.schema["type"] = "integer"
        self.schema["required"] = required


class ListField(SchemaField):
    """List schema field."""

    def __repr__(self):
        return "list"

    def __init__(self, required=False, mandatory_in_list=None, schema=None):
        super().__init__()
        self.schema["type"] = "list"
        self.schema["required"] = required
        self.schema["mandatory_in_list"] = mandatory_in_list
        self.schema["schema"] = schema


class DictField(SchemaField):
    """Dict schema field."""

    def __repr__(self):
        return "dict"

    def __init__(self, required=False, schema=None):
        super().__init__()
        self.schema["type"] = "dict"
        self.schema["required"] = required


class MediaField(SchemaField):
    """Media schema field."""

    def __repr__(self):
        return "media"

    def __init__(self, required=False, schema=None):
        super().__init__()
        self.schema["type"] = "media"
        self.schema["required"] = required


class RelatedContentField(SchemaField):
    """Related Content schema field."""

    def __repr__(self):
        return "related-content"

    def __init__(self, required=False, schema=None):
        super().__init__()
        self.schema["type"] = "related-content"
        self.schema["required"] = required


class StringField(SchemaField):
    """String schema field."""

    def __repr__(self):
        return "string"

    def __init__(self, required=False, maxlength=None, minlength=None):
        super().__init__()
        self.schema["type"] = "string"
        self.schema["required"] = required
        self.schema["minlength"] = minlength
        self.schema["maxlength"] = maxlength
