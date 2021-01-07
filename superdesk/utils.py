# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
import re
import sys
import time
import bcrypt
import hashlib
import base64
import tempfile
import string
import logging

from uuid import uuid4
from datetime import datetime
from bson import ObjectId
from enum import Enum
from importlib import import_module
from eve.utils import config
from superdesk.default_settings import ELASTIC_DATE_FORMAT, ELASTIC_DATETIME_FORMAT
from superdesk.text_utils import get_text


logger = logging.getLogger(__name__)

required_string = {"type": "string", "required": True, "nullable": False, "empty": False}

PWD_ALPHABET = string.ascii_letters + string.digits
PWD_DEFAULT_LENGHT = 40


if sys.version_info < (3, 6):
    logger.warning("Using unsecure password generation, please update to Python 3.6+")
    from random import SystemRandom

    def gen_password(lenght=PWD_DEFAULT_LENGHT):
        sys_random = SystemRandom()
        return "".join(sys_random.choice(PWD_ALPHABET) for _ in range(lenght))


else:
    # "secrets" module is only available with Python 3.6+
    import secrets

    def gen_password(lenght=PWD_DEFAULT_LENGHT):
        return "".join(secrets.choice(PWD_ALPHABET) for _ in range(lenght))


class FileSortAttributes(Enum):
    """
    Enum defining the File Story Attributes.
    """

    fname = 1
    created = 2
    modified = 3


class SortOrder(Enum):
    """
    Enum defining the sort order.
    """

    asc = 1
    desc = 2


class SuperdeskBaseEnum(Enum):
    """
    Base enum
    """

    @classmethod
    def from_value(cls, value):
        """
        Returns the valid enum if value found else none

        :param value: enum value
        :return: return valid
        """
        try:
            return cls(value)
        except ValueError:
            return None

    @classmethod
    def values(cls):
        """
        Returns list of values for an enum

        :return: list of values for an enum
        """
        return [enum_member.value for enum_member in cls]


def get_random_string(length=12):
    return str(uuid4())


def get_random_token(n=40):
    """Generate random token.

    :param n: how many random bytes to generate
    """
    return base64.b64encode(os.urandom(n)).decode()


def import_by_path(path):
    module_path, class_name = path.rsplit(".", 1)
    module = import_module(module_path)
    return getattr(module, class_name)


def get_hash(input_str, salt):
    hashed = bcrypt.hashpw(input_str.encode("UTF-8"), bcrypt.gensalt(salt))
    return hashed.decode("UTF-8")


def get_sorted_files(path, sort_by=FileSortAttributes.fname, sort_order=SortOrder.asc):
    """
    Get the list of files based on the sort order.

    Sort is allowed on name, created and modified datetime

    :param path: directory path
    :param sort_by: "name", "created", "modified"
    :param sort_order: "asc" - ascending, "desc" - descending
    :return: list of files from the path
    """
    # get the files
    files = [file for file in os.listdir(path) if os.path.isfile(os.path.join(path, file))]
    if sort_by == FileSortAttributes.fname:
        files.sort(reverse=(sort_order == SortOrder.desc))
    elif sort_by == FileSortAttributes.created:
        files.sort(key=lambda file: os.path.getctime(os.path.join(path, file)), reverse=(sort_order == SortOrder.desc))
    elif sort_by == FileSortAttributes.modified:
        files.sort(key=lambda file: os.path.getmtime(os.path.join(path, file)), reverse=(sort_order == SortOrder.desc))
    else:
        files.sort(reverse=(sort_order == SortOrder.desc))

    return files


def is_hashed(input_str):
    """Check if given input_str is hashed."""
    return input_str.startswith("$2")


def merge_dicts(dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict, precedence goes to latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def merge_dicts_deep(dict1, dict2):
    """
    Deep merge of two dictionaries.
    Example: merged_dict = dict(merge_dicts_deep(dict1, dict2))

    :param dict1: first dictionary
    :param dict2: second dictionary
    :return: generator which will build a merged dict
    """
    unique_keys = set(dict1.keys()).union(dict2.keys())

    for k in unique_keys:
        # need to merge
        if k in dict1 and k in dict2:
            if isinstance(dict1[k], dict) and isinstance(dict2[k], dict):
                yield (k, dict(merge_dicts_deep(dict1[k], dict2[k])))
            else:
                # if one of the values is not a dict - value from second dict overrides value from first one.
                yield (k, dict2[k])
        elif k in dict1:
            yield (k, dict1[k])
        else:
            yield (k, dict2[k])


class ListCursor(object):
    """Wrapper for a python list as a cursor."""

    def __init__(self, docs=None):
        self.docs = docs if docs else []

    def __getitem__(self, key):
        return self.docs[key]

    def first(self):
        """Get first doc."""
        return self.docs[0] if self.docs else None

    def count(self, **kwargs):
        """Get total count."""
        return len(self.docs)

    def extra(self, response):
        pass


def json_serialize_datetime_objectId(obj):
    """
    Serialize so that objectid and date are converted to appropriate format.
    """
    if isinstance(obj, datetime):
        return str(datetime.strftime(obj, config.DATE_FORMAT))

    if isinstance(obj, ObjectId):
        return str(obj)


def compare_preferences(original, updates):
    original_keys = set(original.keys())
    updates_keys = set(updates.keys())
    intersect_keys = original_keys.intersection(updates_keys)
    added = updates_keys - original_keys
    removed = original_keys - updates_keys
    modified = {o: (original[o], updates[o]) for o in intersect_keys if original[o] != updates[o]}
    return added, removed, modified


def sha(text):
    """Get sha hext digest for given text.

    Using sha256 hashing function, returning 64 hex characters.

    :param text: text str
    """
    return hashlib.sha256(text.encode()).hexdigest()


def plaintext_filter(value):
    """Filter out html from value."""
    return get_text(value).replace("\n", " ").strip()


def format_date(date_string):
    return datetime.strftime(date_string, ELASTIC_DATE_FORMAT)


def format_time(datetime_string):
    return datetime.strftime(datetime_string, ELASTIC_DATETIME_FORMAT)


def save_error_data(data, prefix="superdesk-", suffix=".txt"):
    """Save given data into file and return its name.

    :param data: unicode data
    """
    with tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False) as file:
        file.write(data.encode("utf-8"))
        return file.name


class Timer:
    """
    Stopwatch to measure program execution time in seconds.

    Example:
        >>> t = Timer()
        >>> t.start('retrbinary')
        >>> t.split('retrbinary')
        1.390733003616333
        >>> t.split('retrbinary')
        1.207962989807129
        >>> t.stop('retrbinary')
        4.4189231395721436

    """

    def __init__(self):
        self._stopwatches = {}

    def _validate(self, key):
        if key not in self._stopwatches:
            raise KeyError("Timer was not started or was stopped for {} key.".format(key))

    def start(self, key):
        self._stopwatches[key] = time.time()

    def split(self, key):
        self._validate(key)
        now = time.time()
        delta = now - self._stopwatches[key]
        self._stopwatches[key] = now

        return delta

    def stop(self, key):
        self._validate(key)
        delta = time.time() - self._stopwatches[key]
        del self._stopwatches[key]

        return delta

    def stop_all(self):
        self._stopwatches = {}


def ignorecase_query(word):
    """Case insensitive mongo query."""
    return re.compile("^{}$".format(re.escape(word)), re.IGNORECASE)
