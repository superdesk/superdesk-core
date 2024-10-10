import arrow
from bson import ObjectId
from typing import Any, Callable

from eve.utils import str_to_date
from eve.io.mongo import MongoJSONEncoder
from kombu.serialization import register

from superdesk.core import json
from superdesk.core.types import WSGIApp


CELERY_SERIALIZER_NAME = "context-aware/json"


class ContextAwareSerializerFactory:
    """
    A factory class for creating serializers that automatically handle
    the execution within a specific application context.
    """

    def __init__(self, get_current_app: Callable[[], WSGIApp]):
        """
        Initializes the ContextAwareSerializerFactory with a callable to retrieve the current application context.

        Args:
            get_current_app: A callable that returns the Flask/WSGIApp application context.
        """
        self.get_current_app = get_current_app

    def try_cast(self, value: Any) -> str | Any:
        """
        Tries to cast the given value to an appropriate type (datetime or ObjectId) or returns it unchanged.

        Args:
            v (Any): The value to be casted.

        Returns:
            Any: The casted value, or the original value if no casting was possible.
        """
        if value is None or isinstance(value, bool) or value == 0:
            return value

        try:
            str_to_date(value)
            return arrow.get(value).datetime  # timezone aware time

        except Exception:
            try:
                return ObjectId(value)
            except Exception:
                return value

    def dumps(self, o: Any) -> str:
        """
        Serializes the given object into a JSON string, executing within the application context.

        Args:
            o (Any): The object to serialize.

        Returns:
            str: The serialized JSON string.
        """
        # TODO-ASYNC: Create a JSONEncoder instance without requiring app_context
        # async with self.get_current_app().app_context():
        return MongoJSONEncoder().encode(o)

    def loads(self, s: str) -> Any:
        """
        Deserializes the given JSON string into a Python object, executing within the application context.

        Args:
            s (str): The JSON string to deserialize.

        Returns:
            Any: The deserialized object.
        """
        o = json.loads(s)
        # TODO-ASYNC: Create a JSONDecoder instance without requiring app_context
        # async with self.get_current_app().app_context():
        return self.serialize(o)

    def serialize(self, o: Any) -> Any:
        """
        Recursively serializes complex objects such as lists and dictionaries.

        Args:
            o (Any): The object to serialize.

        Returns:
            Any: The serialized object.
        """

        if isinstance(o, list):
            return [self.serialize(item) for item in o]
        elif isinstance(o, dict):
            if o.get("kwargs") and not isinstance(o["kwargs"], dict):
                o["kwargs"] = json.loads(o["kwargs"])
            return {k: self.serialize(v) for k, v in o.items()}
        else:
            return self.try_cast(o)

    def register_serializer(self, name: str, content_type: str = "application/json") -> None:
        """
            Registers a custom serializer with Kombu, which is used by Celery for message serialization.

        Args:
            name (str): The name under which the serializer should be registered.
            content_type (str): The MIME type associated with the serializer.
        """
        register(name, self.dumps, self.loads, content_type=content_type)
