import arrow

from arrow.parser import ParserError
from bson import ObjectId
from bson.errors import InvalidId
from eve.utils import str_to_date
from eve.io.mongo import MongoJSONEncoder
from eve_elastic import ElasticJSONSerializer
from quart_babel.speaklater import LazyString

from superdesk.core import json
from superdesk.flask import Flask, DefaultJSONProvider


class SuperdeskJSONEncoder(MongoJSONEncoder, ElasticJSONSerializer):
    """Custom JSON encoder for elastic that can handle `bson.ObjectId`s."""

    def default(self, obj):
        if isinstance(obj, LazyString):
            return str(obj)
        return super().default(obj)


class SuperdeskFlaskJSONProvider(DefaultJSONProvider, SuperdeskJSONEncoder):
    """
    Custom JSON provider for flask that can handle `bson.ObjectId`s
    and bunch of other complex types.

    This provider attempts to serialize objects using custom encoders for MongoDB
    and Elasticsearch types before falling back to the default Flask JSON encoder.
    """

    def __init__(self, app: Flask):
        """
        Initialize the SuperdeskFlaskJSONProvider.

        The initialization explicitly calls the __init__ method of DefaultJSONProvider
        to ensure compatibility with Flask 3.0's new way of setting custom JSON providers.
        """

        DefaultJSONProvider.__init__(self, app)  # type: ignore  # mypy is not seeing Flask as App here

    def default(self, obj):
        try:
            return super(SuperdeskJSONEncoder, self).default(obj)
        except TypeError:
            return super(DefaultJSONProvider, self).default(obj)


def try_cast(v):
    """Cast string value to date or ObjectId if possible.

    :param v: string value
    """
    try:
        str_to_date(v)  # try if it matches format
        return arrow.get(v).datetime  # return timezone aware time
    except (ValueError, ParserError):
        try:
            return ObjectId(v)
        except InvalidId:
            return v


def cast_item(o):
    if isinstance(o, (int, float, bool)):
        return o
    elif isinstance(o, str):
        return try_cast(o)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            o[i] = cast_item(v)
        return o
    elif isinstance(o, dict):
        for k, v in o.items():
            o[k] = cast_item(v)
        return o
    else:
        return o


def loads(s):
    o = json.loads(s)

    if isinstance(o, list):
        for i, v in enumerate(o):
            o[i] = cast_item(v)
        return o
    elif isinstance(o, dict):
        for k, v in o.items():
            o[k] = cast_item(v)
        return o
    else:
        return cast_item(o)


def dumps(o):
    return MongoJSONEncoder().encode(o)
