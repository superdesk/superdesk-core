import json
import string
import random

from eve.utils import ParsedRequest
from eve.io.mongo import MongoJSONEncoder

from apps.dictionaries.service import words, DictionaryService, store_dict, fetch_dict, FILE_ID
from superdesk import get_resource_service
from superdesk.tests import TestCase


class WordsTestCase(TestCase):
    def setUp(self):
        self.req = ParsedRequest()
        with self.app.test_request_context(self.app.config.get("URL_PREFIX")):
            self.dictionaries = [
                {"_id": "1", "name": "Eng", "language_id": "en"},
                {"_id": "2", "name": "Eng AUs", "language_id": "en-AU", "is_active": "true"},
                {"_id": "3", "name": "French", "language_id": "fr"},
            ]
            self.app.data.insert("dictionaries", self.dictionaries)

    def test_words_parsing(self):
        self.assertEquals(["abc"], words("abc"))
        self.assertEqual(["abc bce"], words("abc bce"))
        self.assertEqual(["abc bce", "wer tyu"], words("abc bce\nwer tyu"))
        self.assertEqual(["you'd"], words("you'd"))
        self.assertEqual(["you'd", "will"], words("you'd\nwill"))

    def test_base_language(self):
        self.assertEqual(DictionaryService().get_base_language("en-AU"), "en")
        self.assertIsNone(DictionaryService().get_base_language("en"))

    def test_get_dictionary(self):
        with self.app.app_context():
            dicts = get_resource_service("dictionaries").get_dictionaries("en")
            self.assertEqual(len(dicts), 1)
            self.assertEqual(dicts[0]["language_id"], "en")
            dicts = get_resource_service("dictionaries").get_dictionaries("en-AU")
            self.assertEqual(len(dicts), 1)
            self.assertEqual(dicts[0]["language_id"], "en-AU")

    def test_store_dict_small(self):
        content = {"foo": 1}
        dictionary = {"content": content}
        store_dict(dictionary, {})
        self.assertEqual(json.dumps(content), dictionary.get("content"))
        self.assertEqual(content, fetch_dict(dictionary))

    def test_store_dict_big(self):
        content = self._get_big_dict()
        dictionary = {"content": content}
        self.assertGreater(len(json.dumps(dictionary, cls=MongoJSONEncoder)), 1000000)
        store_dict(dictionary, {})
        self.assertIsNone(dictionary["content"])
        self.assertEqual(content, fetch_dict(dictionary))
        self.assertLess(len(json.dumps(dictionary, cls=MongoJSONEncoder)), 100)

    def test_store_big_after_small(self):
        original = {"content": {"foo": 1}}
        updates = {"content": self._get_big_dict()}
        store_dict(updates, original)
        self.assertIsNone(updates["content"])
        self.assertIsNotNone(updates[FILE_ID])

    def test_small_after_big(self):
        updates = {"content": self._get_big_dict()}
        store_dict(updates, {})
        file_id = updates[FILE_ID]
        self.assertIsNotNone(self.app.storage.get(file_id))

        original = updates
        updates = {"content": {"foo": 1}}
        store_dict(updates, original)

        self.assertIsNone(updates[FILE_ID])
        self.assertEqual(json.dumps({"foo": 1}), updates["content"])
        self.assertIsNone(self.app.storage.get(file_id))

    def _get_big_dict(self):
        word = "".join([random.choice(string.ascii_letters) for i in range(1000000)])
        return {word: 1}
