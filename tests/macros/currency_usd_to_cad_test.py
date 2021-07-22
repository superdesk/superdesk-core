import unittest
from decimal import Decimal

from superdesk.macros.currency_usd_to_cad import usd_to_cad


class CurrencyTestCase(unittest.TestCase):
    def test_usd_to_cad(self):
        item = {"body_html": "$100"}
        res, diff = usd_to_cad(item, rate=Decimal(2))
        self.assertTrue("$100" in diff)
        self.assertEqual(diff["$100"], "$100 (CAD 200)")
