# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import io
import re
import logging
import collections

from flask import json, current_app as app
from eve.utils import config

from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError
from apps.dictionaries.resource import DICTIONARY_FILE, DictionaryType


FILE_ID = '_file_id'


logger = logging.getLogger(__name__)


def encode_dict(words_dict):
    return json.dumps(words_dict)


def decode_dict(words_list):
    if isinstance(words_list, dict):
        return words_list
    return json.loads(words_list)


def train(features):
    model = collections.defaultdict(lambda: 1)
    for f in features:
        model[f] += 1
    return model


def words(text):
    return [w.strip() for w in re.findall('[^\n]+', text) if not w.isdigit()]


def add_word(words, word, count):
    """Add word with count to words model.

    :param words: words model
    :param word
    :param count
    """
    words.setdefault(word, 0)
    try:
        words[word] += count
    except TypeError as e:
        logger.error(word)
        logger.error(count)
        raise e


def add_words(nwords, text, val=1):
    for word in words(text):
        add_word(nwords, word, val)


def read(stream):
    return stream.read().decode('utf-8').replace('\ufeff', '')


def merge(doc, words):
    doc.setdefault('content', {})
    for word, count in words.items():
        add_word(doc['content'], word, count)


def fetch_dict(doc):
    """Fetch dictionary content after storing it, from gridfs or json.

    :param doc
    """
    if doc and doc.get(FILE_ID):
        content_file = app.storage.get(doc[FILE_ID])
        content = json.loads(content_file.read())
        return content

    if doc and doc.get('content'):
        return decode_dict(doc['content'])

    return {}


def store_dict(updates, original):
    """Store dictionary content.

    In case it's too big - use gridfs, otherwise just json encode it.

    :param updates
    :param original
    """
    content = updates.pop('content', {})
    if content:
        content_json = json.dumps(content)
        if is_big(content_json):
            content_binary = io.BytesIO(content_json.encode('utf-8'))
            updates[FILE_ID] = app.storage.put(content_binary)
            updates['content'] = None
        else:
            updates['content'] = content_json
            updates[FILE_ID] = None

    if original.get(FILE_ID):
        app.storage.delete(original[FILE_ID])


def is_big(json_data):
    """Test if given json data is too big for mongo document.

    Using 1MB as limit atm.

    :param json_data
    """
    return len(json_data) > 1000000


def read_from_file(doc):
    """Read from plain text file

    One word per line
    UTF-8 encoding
    """
    content = doc.pop(DICTIONARY_FILE)
    if 'text/' not in content.mimetype:
        raise SuperdeskApiError.badRequestError('A text dictionary file is required')
    return train(words(read(content)))


class DictionaryService(BaseService):
    def on_create(self, docs):
        for doc in docs:
            if self.find_one(req=None, name=doc['name'],
                             language_id=doc['language_id'],
                             type=doc.get('type', DictionaryType.DICTIONARY.value)):
                raise SuperdeskApiError.badRequestError(message='The dictionary already exists',
                                                        payload={'name': 'duplicate'})
            self.__set_default(doc)
            self._validate_dictionary(doc)

            if doc.get(DICTIONARY_FILE):
                words = read_from_file(doc)
                merge(doc, words)

            store_dict(doc, {})

    def find_one(self, req, **lookup):
        doc = super().find_one(req, **lookup)
        if doc:
            doc['content'] = fetch_dict(doc)
        return doc

    def _validate_dictionary(self, updates, original={}):
        dict_type = updates.get('type', original.get('type', DictionaryType.DICTIONARY.value))
        if dict_type == DictionaryType.ABBREVIATIONS.value and not updates.get('user', original.get('user')):
            raise SuperdeskApiError.badRequestError(message='User is required for the abbreviations dictionary.',
                                                    payload={'user': 'missing'})

        if original and dict_type != original.get('type', DictionaryType.DICTIONARY.value):
            raise SuperdeskApiError.badRequestError(message='The dictionary type cannot be changed.')

    def get_base_language(self, lang):
        if lang and lang.find('-') > 0:
            return lang.split('-')[0]

    def get_dictionaries(self, lang):
        """Returns all the active dictionaries.

        If both the language (en-AU)
        and the base language (en) available, it will return the dict with language

        :param lang:
        :return:
        """
        languages = [{'language_id': lang}]
        base_language = self.get_base_language(lang)
        if base_language:
            languages.append({'language_id': base_language})

        lookup = {'$and': [{'$or': languages},
                           {'$or': [{'is_active': {'$exists': 0}}, {'is_active': 'true'}]},
                           {'$or': [{'type': {'$exists': 0}}, {'type': DictionaryType.DICTIONARY.value}]}]}
        dicts = list(self.get(req=None, lookup=lookup))
        langs = [d['language_id'] for d in dicts]

        if base_language and base_language in langs and lang in langs:
            dicts = [d for d in dicts if d['language_id'] != base_language]

        return dicts

    def get_model_for_lang(self, lang):
        """Get model for given language.

        It will use all active dictionaries for given language combined.

        :param lang: language code
        """
        model = {}
        dicts = self.get_dictionaries(lang)

        for _dict in dicts:
            content = fetch_dict(_dict)
            for word, count in content.items():
                add_word(model, word, count)
        return model

    def on_update(self, updates, original):
        # parse json list
        if updates.get('content_list'):
            updates['content'] = json.loads(updates.pop('content_list'))

        if 'type' not in original:
            self.__set_default(updates)

        self._validate_dictionary(updates, original)

        # handle manual changes
        if original.get('type', DictionaryType.DICTIONARY.value) == DictionaryType.DICTIONARY.value:
            nwords = fetch_dict(original).copy()
            for word, val in updates.get('content', {}).items():
                if val:
                    add_words(nwords, word, val)
                else:
                    nwords.pop(word, None)

            updates['content'] = nwords

        # handle uploaded file
        if updates.get(DICTIONARY_FILE):
            file_words = read_from_file(updates)
            merge(updates, file_words)

        store_dict(updates, original)

    def __set_default(self, doc):
        if 'type' not in doc:
            doc['type'] = DictionaryType.DICTIONARY.value

    def on_fetched_item(self, doc):
        self.__enhance_items([doc])

    def on_fetched(self, docs):
        self.__enhance_items(docs[config.ITEMS])

    def __enhance_items(self, docs):
        for doc in docs:
            self.__set_default(doc)
