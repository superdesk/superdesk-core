import unittest
import superdesk.utils as utils


class UtilsTestCase(unittest.TestCase):
    def test_sha(self):
        digest = utils.sha("some text")
        self.assertGreater(len(digest), 40)

    def test_get_random_token(self):
        token = utils.get_random_token()
        self.assertGreater(len(token), 20)
        self.assertNotEqual(token, utils.get_random_token())

    def test_save_error_data(self):
        filename = utils.save_error_data("foo")
        self.assertIn("superdesk", filename)
        with open(filename) as f:
            self.assertEqual("foo", f.read())

    def test_timer(self):
        timer = utils.Timer()

        timer.start("test")
        self.assertIsNotNone(timer.split("test"))
        self.assertIsNotNone(timer.split("test"))
        self.assertIsNotNone(timer.stop("test"))
        self.assertRaises(KeyError, timer.split, "test")
        self.assertRaises(KeyError, timer.split, "bla")

    def test_allowed_container(self):
        container = utils.AllowedContainer({"foo": 1})
        self.assertIn("foo", container)
        self.assertNotIn("bar", container)
        allowed = [x for x in container]
        self.assertEqual(["foo"], allowed)

    def test_list_chunks(self):
        items = [1, 2, 3, 4, 5]
        chunks = utils.get_list_chunks(items, 1)
        assert [[1], [2], [3], [4], [5]] == chunks
        chunks = utils.get_list_chunks(items, 2)
        assert [[1, 2], [3, 4], [5]] == chunks
        chunks = utils.get_list_chunks(items, 5)
        assert [[1, 2, 3, 4, 5]] == chunks
        chunks = utils.get_list_chunks(items, 10)
        assert [[1, 2, 3, 4, 5]] == chunks


class JoinUrlPartsTestCase(unittest.TestCase):
    def test_join_url_parts_basic(self):
        """Test basic URL path joining"""
        self.assertEqual(utils.join_url_parts("api", "v1", "items"), "api/v1/items")

    def test_join_url_parts_with_slashes(self):
        """Test joining parts that contain leading/trailing slashes"""
        self.assertEqual(utils.join_url_parts("/api/", "/v1/", "/items/"), "api/v1/items")

    def test_join_url_parts_empty_parts(self):
        """Test joining with empty parts"""
        self.assertEqual(utils.join_url_parts("api", "", "items"), "api/items")
        self.assertEqual(utils.join_url_parts("", "api", "items"), "api/items")
        self.assertEqual(utils.join_url_parts("api", "items", ""), "api/items")

    def test_join_url_parts_single_part(self):
        """Test joining a single part"""
        self.assertEqual(utils.join_url_parts("api"), "api")

    def test_join_url_parts_no_parts(self):
        """Test joining with no parts"""
        self.assertEqual(utils.join_url_parts(), "")

    def test_join_url_parts_multiple_slashes(self):
        """Test joining parts with multiple slashes"""
        self.assertEqual(utils.join_url_parts("api//", "//v1//", "//items"), "api/v1/items")

    def test_join_url_parts_internal_slashes(self):
        """Test joining parts that contain internal slashes that should be preserved"""
        self.assertEqual(utils.join_url_parts("api", "v1/latest", "items"), "api/v1/latest/items")
        self.assertEqual(utils.join_url_parts("/api/", "v1/latest/", "/items/"), "api/v1/latest/items")
