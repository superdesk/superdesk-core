
import unittest

from apps.comments.user_mentions import get_mentions


class CommentsTestCase(unittest.TestCase):


    def test_user_mentions(self):
        users, desks = get_mentions('hello @petr.jasek and #sports.desk')
        self.assertIn('petr.jasek', users)
        self.assertIn('sports.desk', desks)
