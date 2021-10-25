import superdesk
from superdesk.tests import TestCase


class VocabulariesServiceGetItemsTestCase(TestCase):
    def setUp(self):
        self.app.data.insert(
            "vocabularies",
            [
                {
                    "_id": "funny-keywords",
                    "items": [
                        {
                            "name": "BRIEF",
                            "qcode": "BRIEF",
                            "is_active": False,
                            "translations": {"name": {"nl": "BRIEF", "fr": "BRIEF"}},
                        },
                        {
                            "name": "PREVIEW",
                            "qcode": "PREVIEW",
                            "is_active": True,
                            "translations": {"name": {"nl": "Voorbericht", "fr": "Avant-Papier"}},
                        },
                        {
                            "name": "WEST FLANDERS",
                            "qcode": "WEST FLANDERS",
                            "is_active": True,
                            "translations": {"name": {"nl": "West-Vlaanderen", "fr": "Flandre occidentale"}},
                        },
                        {
                            "name": "EAST FLANDERS",
                            "qcode": "EAST FLANDERS",
                            "is_active": False,
                            "translations": {"name": {"nl": "Oost-Vlaanderen", "fr": "Flandre orientale"}},
                        },
                        {
                            "name": "ANTWERP",
                            "qcode": "ANTWERP",
                            "is_active": True,
                            "translations": {"name": {"nl": "Antwerpen", "fr": "Anvers"}},
                        },
                    ],
                },
                {
                    "_id": "sad-keywords",
                    "items": [
                        {
                            "name": "WALLOON BRABANT",
                            "qcode": "WALLOON BRABANT",
                            "is_active": True,
                            "translations": {"name": {"nl": "Waals-Brabant", "fr": "Brabant wallon"}},
                        },
                        {
                            "name": "BIOGRAPHY",
                            "qcode": "BIOGRAPHY",
                            "is_active": True,
                            "translations": {"name": {"nl": "Biografie", "fr": "Biographie"}},
                        },
                        {
                            "name": "WEATHER",
                            "qcode": "WEATHER",
                            "is_active": True,
                            "translations": {"name": {"nl": "Weer", "fr": "Météo"}},
                        },
                    ],
                },
            ],
        )

    def test_search_by_id(self):
        items = superdesk.get_resource_service("vocabularies").get_items(_id="funny-keywords")
        self.assertEqual(len(items), 3)

        items = superdesk.get_resource_service("vocabularies").get_items(_id="sad-keywords")
        self.assertEqual(len(items), 3)

        items = superdesk.get_resource_service("vocabularies").get_items(_id="not-found-id")
        self.assertEqual(items, [])

    def test_search_by_qcode(self):
        items = superdesk.get_resource_service("vocabularies").get_items(_id="funny-keywords", qcode="PREVIEW")
        self.assertEqual(
            items,
            [
                {
                    "name": "PREVIEW",
                    "qcode": "PREVIEW",
                    "scheme": "funny-keywords",
                    "translations": {"name": {"nl": "Voorbericht", "fr": "Avant-Papier"}},
                }
            ],
        )
        items = superdesk.get_resource_service("vocabularies").get_items(_id="funny-keywords", qcode="not found")
        self.assertEqual(items, [])

    def test_search_by_is_active(self):
        items = superdesk.get_resource_service("vocabularies").get_items(_id="funny-keywords", is_active=False)
        self.assertEqual(len(items), 2)

        items = superdesk.get_resource_service("vocabularies").get_items(_id="funny-keywords", is_active=True)
        self.assertEqual(len(items), 3)

    def test_search_by_name(self):
        items = superdesk.get_resource_service("vocabularies").get_items(
            _id="funny-keywords", name="BRIEF", is_active=False
        )
        self.assertEqual(
            items,
            [
                {
                    "name": "BRIEF",
                    "qcode": "BRIEF",
                    "scheme": "funny-keywords",
                    "translations": {"name": {"nl": "BRIEF", "fr": "BRIEF"}},
                }
            ],
        )

        items = superdesk.get_resource_service("vocabularies").get_items(_id="funny-keywords", name="not found")
        self.assertEqual(items, [])

    def test_search_by_translation_name(self):
        items = superdesk.get_resource_service("vocabularies").get_items(
            _id="funny-keywords",
            name="Avant-Papier",
            lang="fr",
        )
        self.assertEqual(
            items,
            [
                {
                    "name": "PREVIEW",
                    "qcode": "PREVIEW",
                    "scheme": "funny-keywords",
                    "translations": {"name": {"nl": "Voorbericht", "fr": "Avant-Papier"}},
                }
            ],
        )

        items = superdesk.get_resource_service("vocabularies").get_items(
            _id="funny-keywords",
            name="AVANT-PAPIER",
            lang="fr",
        )
        self.assertEqual(
            items,
            [
                {
                    "name": "PREVIEW",
                    "qcode": "PREVIEW",
                    "scheme": "funny-keywords",
                    "translations": {"name": {"nl": "Voorbericht", "fr": "Avant-Papier"}},
                }
            ],
        )

        items = superdesk.get_resource_service("vocabularies").get_items(
            _id="funny-keywords",
            name="Avant-Papier-bla-bla",
            lang="fr",
        )
        self.assertEqual(items, [])

    def test_search_by_all_fields(self):
        items = superdesk.get_resource_service("vocabularies").get_items(
            _id="funny-keywords",
            qcode="PREVIEW",
            name="Avant-Papier",
            lang="fr",
            is_active=True,
        )
        self.assertEqual(
            items,
            [
                {
                    "name": "PREVIEW",
                    "qcode": "PREVIEW",
                    "scheme": "funny-keywords",
                    "translations": {"name": {"nl": "Voorbericht", "fr": "Avant-Papier"}},
                }
            ],
        )

        items = superdesk.get_resource_service("vocabularies").get_items(
            _id="funny-keywords",
            qcode="PREVIEW",
            name="Avant-Papier",
            lang="fr",
            is_active=False,
        )
        self.assertEqual(items, [])
