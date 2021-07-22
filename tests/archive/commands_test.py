from superdesk.tests import TestCase
from apps.archive.commands import RemoveExpiredContent


class RemoveExpiredContentTestCase(TestCase):
    def test_is_expired(self):
        command = RemoveExpiredContent()
        item = {"expiry": None, "_id": "foo"}
        self.assertFalse(command._can_remove_item(item))
