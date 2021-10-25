from superdesk.tests import TestCase
from apps.rules.routing_rules import RoutingRuleSchemeService


class SetDefaultValuesTestCase(TestCase):
    def test_setting_default_values(self):

        instance = RoutingRuleSchemeService()
        category = [{"qcode": "a", "name": "Australian General News"}]
        result = instance._assign_default_values({"anpa_category": category}, None)
        self.assertEqual(result["anpa_category"], [{"qcode": "a", "name": "Australian General News"}])

        with self.app.app_context():
            result = instance._assign_default_values({}, None)
            self.assertIsNone(result["anpa_category"])

            result = instance._assign_default_values({}, [{"qcode": "a", "name": "Australian General News"}])
            self.assertEqual(result["anpa_category"], [{"qcode": "a", "name": "Australian General News"}])

    def test_getting_selected_categories(self):
        vocabularies = [
            {
                "_id": "categories",
                "items": [
                    {"qcode": "a", "name": "foo", "is_active": True},
                    {"qcode": "b", "name": "bar", "is_active": True},
                    {"qcode": "c", "name": "baz", "is_active": False},
                ],
            }
        ]

        instance = RoutingRuleSchemeService()

        with self.app.app_context():
            self.app.data.insert("vocabularies", vocabularies)
            result = instance._get_categories("a")
            self.assertEqual(result, [{"qcode": "a", "name": "foo"}])

            result = instance._get_categories("a,b")
            self.assertEqual(result, [{"qcode": "a", "name": "foo"}, {"qcode": "b", "name": "bar"}])

            result = instance._get_categories("a,c")
            self.assertEqual(result, [{"qcode": "a", "name": "foo"}])

            result = instance._get_categories("c")
            self.assertEqual(result, [])

            result = instance._get_categories(None)
            self.assertIsNone(result)
