
from superdesk.utc import utcnow
from superdesk.tests import TestCase

from .html_newsml_g2_formatter import HTMLNewsMLG2Formatter


class HTMLNewsmlG2FormatterTestCase(TestCase):

    article = {
        'guid': 'tag:aap.com.au:20150613:12345',
        '_current_version': 1,
        'anpa_category': [
            {
                'qcode': 'a',
                'name': 'Australian General News'
            }
        ],
        'source': 'AAP',
        'headline': 'This is a test headline',
        'byline': 'joe',
        'slugline': 'slugline',
        'subject': [{'qcode': '02011001', 'name': 'international court or tribunal'},
                    {'qcode': '02011002', 'name': 'extradition'}],
        'anpa_take_key': 'take_key',
        'unique_id': '1',
        'body_html': '<p>The story body <b>HTML</b></p>',
        'type': 'text',
        'word_count': '1',
        'priority': '1',
        '_id': 'urn:localhost.abc',
        'state': 'published',
        'urgency': 2,
        'pubstatus': 'usable',
        'dateline': {
            'source': 'AAP',
            'text': 'Los Angeles, Aug 11 AAP -',
            'located': {
                'alt_name': '',
                'state': 'California',
                'city_code': 'Los Angeles',
                'city': 'Los Angeles',
                'dateline': 'city',
                'country_code': 'US',
                'country': 'USA',
                'tz': 'America/Los_Angeles',
                'state_code': 'CA'
            }
        },
        'creditline': 'sample creditline',
        'keywords': ['traffic'],
        'abstract': 'sample abstract',
        'place': [{'qcode': 'Australia', 'name': 'Australia',
                   'state': '', 'country': 'Australia',
                   'world_region': 'Oceania'}],
        'company_codes': [{'name': 'YANCOAL AUSTRALIA LIMITED', 'qcode': 'YAL', 'security_exchange': 'ASX'}],
    }

    subscriber = {'_id': 'foo', 'name': 'Foo'}

    def get_article(self):
        article = self.article.copy()
        article['firstcreated'] = article['versioncreated'] = utcnow()
        return article

    def test_html_content(self):
        formatter = HTMLNewsMLG2Formatter()
        article = self.get_article()
        _, doc = formatter.format(article, self.subscriber)[0]
        self.assertIn('<body>%s</body>' % article['body_html'], doc)
        self.assertIn('<title>%s</title>' % article['headline'], doc)
