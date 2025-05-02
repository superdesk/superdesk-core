from superdesk.tests import TestCase
from superdesk.utc import utcnow
from apps.archive.commands import RemoveExpiredContent


class RemoveExpiredContentTestCase(TestCase):
    async def test_is_expired(self):
        command = RemoveExpiredContent()
        item = {"expiry": None, "_id": "foo"}
        now = utcnow()
        self.assertFalse(await command._can_remove_item(item, now))
