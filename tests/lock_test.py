import time

from superdesk.tests import TestCase
from superdesk.lock import lock, unlock, touch


class LockTestCase(TestCase):
    def test_lock(self):
        task = "test"

        self.assertTrue(lock(task, expire=2))
        self.assertFalse(lock(task))

        time.sleep(2)

        # lock again after expiry
        self.assertTrue(lock(task, expire=1))
        self.assertTrue(touch(task, expire=10))

        time.sleep(2)

        # can't lock after touch
        self.assertFalse(lock(task))

        unlock(task)

        # can't touch after unlock
        self.assertFalse(touch(task))

        # unlocking again is noop
        unlock(task)

        # locking after unlocking
        self.assertTrue(lock(task, expire=1))
