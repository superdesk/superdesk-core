
from superdesk.tests import TestCase
from superdesk.vocabularies.commands import get_vocabularies, is_changed, update_item


class UpdateArchiveVocabulariesTestCase(TestCase):
    fields = ['subject', 'genre', 'place', 'anpa_category']
    vocabularies_list = [
        {
            '_id': 'country_custom',
            'items': [
                {
                    'name': 'Australia',
                    'qcode': 'country_custom:1001001',
                    'is_active': True,
                    'translations': {
                        'name': {
                            'de': 'Australien',
                            'it': 'Australia',
                            'ja': 'オーストラリア'
                        }
                    }
                },
                {
                    'name': 'Austria',
                    'qcode': 'country_custom:1001002',
                    'is_active': True,
                    'translations': {
                        'name': {
                            'de': 'Österreich',
                            'it': 'Austria',
                            'ja': 'オーストリア'
                        }
                    }
                }
            ]
        },

        {
            '_id': 'subject_custom',
            'items': [
                {
                    'name': 'Asset allocation',
                    'parent': None,
                    'is_active': True,
                    'qcode': 'subject:01000000',
                    'translations': {
                        'name': {
                            'de': 'Asset-Allokation',
                            'it': 'Asset allocation',
                            'ja': 'アセット・アロケーション'
                        }
                    }
                },
                {
                    'name': 'Risk',
                    'parent': None,
                    'is_active': True,
                    'qcode': 'subject:02000000',
                    'translations': {
                        'name': {
                            'de': 'Risiko',
                            'it': 'Rischio',
                            'ja': 'リスク'
                        }
                    }
                },
                {
                    'name': 'Market context',
                    'parent': None,
                    'is_active': True,
                    'qcode': 'subject:03000000',
                    'translations': {
                        'name': {
                            'de': 'Marktumfeld',
                            'it': 'Contesto di mercato',
                            'ja': 'マーケット・コンテクスト'
                        }
                    }
                }
            ]
        }
    ]

    def test_get_vocabularies(self):
        vocabularies = get_vocabularies(self.vocabularies_list)

        self.assertTrue('country_custom' in vocabularies)
        self.assertTrue('values' in vocabularies['country_custom'])
        self.assertTrue('country_custom:1001001' in vocabularies['country_custom']['values'])
        self.assertTrue('country_custom:1001002' in vocabularies['country_custom']['values'])
        self.assertTrue(
            vocabularies['country_custom']['values']['country_custom:1001001']['scheme'] == 'country_custom'
        )
        self.assertTrue(
            vocabularies['country_custom']['values']['country_custom:1001002']['scheme'] == 'country_custom'
        )

        self.assertTrue('subject_custom' in vocabularies)
        self.assertTrue('values' in vocabularies['subject_custom'])
        self.assertTrue('values' in vocabularies['subject_custom'])
        self.assertTrue('subject:01000000' in vocabularies['subject_custom']['values'])
        self.assertTrue('subject:02000000' in vocabularies['subject_custom']['values'])
        self.assertTrue('subject:03000000' in vocabularies['subject_custom']['values'])
        self.assertTrue(vocabularies['subject_custom']['values']['subject:01000000']['scheme'] == 'subject_custom')
        self.assertTrue(vocabularies['subject_custom']['values']['subject:02000000']['scheme'] == 'subject_custom')
        self.assertTrue(vocabularies['subject_custom']['values']['subject:03000000']['scheme'] == 'subject_custom')

    def test_is_changed(self):
        old = {
            'name': 'Market context',
            'parent': None,
            'qcode': 'subject:03000000',
            'translations': {'name': {'de': 'Marktumfeld', 'it': 'Contesto di mercato', 'ja': 'マーケット・コンテクスト'}}
        }

        new = {
            'name': 'Market context',
            'parent': None,
            'qcode': 'subject:03000000',
            'translations': {'name': {'de': 'changed', 'it': 'Contesto di mercato', 'ja': 'マーケット・コンテクスト'}}
        }

        new_no_translations = {
            'name': 'Market context',
            'parent': None,
            'qcode': 'subject:03000000'
        }

        self.assertTrue(is_changed(old, {}))
        self.assertTrue(is_changed(old, {'name': 'Market context'}))
        self.assertTrue(is_changed(old, new_no_translations))
        self.assertFalse(is_changed(old, old))
        self.assertTrue(is_changed(old, new))

    def test_update_item(self):
        vocabularies = get_vocabularies(self.vocabularies_list)

        item = {
            'place': [
                self.vocabularies_list[0]['items'][0],
                self.vocabularies_list[0]['items'][0]
            ],
            'subject': [
                self.vocabularies_list[1]['items'][1],
                self.vocabularies_list[1]['items'][1]
            ]
        }

        item['subject'][0]['scheme'] = 'country_custom'
        item['subject'][0]['scheme'] = 'country_custom'
        item['place'][0]['scheme'] = 'subject_custom'
        item['place'][0]['scheme'] = 'subject_custom'
        changed = {'qcode': 'subject:03000000', 'scheme': 'subject_custom'}
        item['subject'].append(changed)

        updates = update_item(item, vocabularies, self.fields)

        self.assertTrue('subject' in updates)
        self.assertTrue(updates['subject'][0].get('qcode') == 'subject:03000000')
        self.assertTrue('translations' in updates['subject'][0])
