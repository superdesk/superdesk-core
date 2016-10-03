
import arrow
import superdesk

from flask import json
from bson import ObjectId
from bson.errors import InvalidId
from eve.utils import str_to_date
from eve.io.mongo import MongoJSONEncoder
from eve_elastic import ElasticJSONSerializer


class SuperdeskJSONEncoder(MongoJSONEncoder, ElasticJSONSerializer):
    """Custom JSON encoder for elastic that can handle `bson.ObjectId`s."""

    pass


def try_cast(v):
    """Cast string value to date or ObjectId if possible.

    :param v: string value
    """
    try:
        str_to_date(v)  # try if it matches format
        return arrow.get(v).datetime  # return timezone aware time
    except ValueError:
        try:
            return ObjectId(v)
        except InvalidId:
            return v


def cast_item(o):
    with superdesk.app.app_context():
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
    with superdesk.app.app_context():
        return MongoJSONEncoder().encode(o)
