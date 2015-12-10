# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import superdesk
from eve.utils import config
from superdesk.publish.formatters import Formatter
from superdesk.errors import FormatterError
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, EMBARGO
from superdesk.metadata.packages import RESIDREF, GROUP_ID, GROUPS, ROOT_GROUP, REFS
from superdesk.utils import json_serialize_datetime_objectId


def filter_empty_vals(data):
    """Filter out `None` values from a given dict."""
    return dict(filter(lambda x: x[1], data.items()))


def format_cv_item(item):
    """Format item from controlled vocabulary for output."""
    return filter_empty_vals({
        'code': item.get('qcode'),
        'name': item.get('name'),
    })


class NINJSFormatter(Formatter):
    """
    NINJS Formatter
    """
    direct_copy_properties = ('versioncreated', 'usageterms', 'language', 'headline',
                              'urgency', 'pubstatus', 'mimetype', 'place', 'copyrightholder',
                              'body_text', 'body_html', 'profile', 'slugline', 'keywords')

    rendition_properties = ('href', 'width', 'height', 'mimetype')

    def format(self, article, subscriber):
        try:
            pub_seq_num = superdesk.get_resource_service('subscribers').generate_sequence_number(subscriber)

            ninjs = {
                '_id': article['_id'],
                'version': str(article.get(config.VERSION, 1)),
                'type': self._get_type(article)
            }

            try:
                ninjs['byline'] = self._get_byline(article)
            except:
                pass

            located = article.get('dateline', {}).get('located', {})
            if located:
                ninjs['located'] = located.get('city', '')

            for copy_property in self.direct_copy_properties:
                if article.get(copy_property) is not None:
                    ninjs[copy_property] = article[copy_property]

            if article.get('body_html'):
                ninjs['body_html'] = self.append_body_footer(article)

            if article.get('description'):
                ninjs['description_html'] = self.append_body_footer(article)

            if article[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
                ninjs['associations'] = self._get_associations(article)
            elif article.get('associations', {}):
                ninjs['associations'] = self._format_related(article, subscriber)

            if article.get(EMBARGO):
                ninjs['embargoed'] = article.get(EMBARGO).isoformat()

            if article.get('priority'):
                ninjs['priority'] = article['priority']
            else:
                ninjs['priority'] = 5

            if article.get('subject'):
                ninjs['subject'] = self._get_subject(article)

            if article.get('anpa_category'):
                ninjs['service'] = self._get_service(article)

            if article.get('renditions'):
                ninjs['renditions'] = self._get_renditions(article)

            if article.get('abstract'):
                ninjs['description_text'] = article.get('abstract')
            elif article.get('description_text'):
                ninjs['description_text'] = article.get('description_text')

            if article.get('company_codes'):
                ninjs['organisation'] = [{'name': c.get('name', ''), 'rel': 'Securities Identifier',
                                          'symbols': [{'ticker': c.get('qcode', ''),
                                                       'exchange': c.get('security_exchange', '')}]}
                                         for c in article['company_codes']]

            return [(pub_seq_num, json.dumps(ninjs, default=json_serialize_datetime_objectId))]
        except Exception as ex:
            raise FormatterError.ninjsFormatterError(ex, subscriber)

    def can_format(self, format_type, article):
        return format_type == 'ninjs'

    def _get_byline(self, article):
        if 'byline' in article:
            return article['byline'] or ''
        user = superdesk.get_resource_service('users').find_one(req=None, _id=article['original_creator'])
        if user:
            return user['display_name'] or ''
        raise Exception('User not found')

    def _get_type(self, article):
        if article[ITEM_TYPE] == CONTENT_TYPE.PREFORMATTED:
            return CONTENT_TYPE.TEXT
        return article[ITEM_TYPE]

    def _get_associations(self, article):
        """Create associations dict for package groups."""
        associations = dict()
        for group in article[GROUPS]:
            if group[GROUP_ID] == ROOT_GROUP:
                continue

            for ref in group[REFS]:
                if RESIDREF in ref:
                    items = associations.get(group[GROUP_ID], [])
                    item = {}
                    item['_id'] = ref[RESIDREF]
                    item[ITEM_TYPE] = ref[ITEM_TYPE]
                    items.append(item)
                    associations[group[GROUP_ID]] = items
        return associations

    def _format_related(self, article, subscriber):
        """Format all associated items for simple items (not packages)."""
        associations = {}
        for key, item in article.get('associations', {}).items():
            seq, formatted = self.format(item, subscriber)[0]
            associations[key] = json.loads(formatted)
        return associations

    def _get_subject(self, article):
        """Get subject list for article."""
        return [format_cv_item(item) for item in article.get('subject', [])]

    def _get_service(self, article):
        """Get service list for article.

        It's using `anpa_category` to populate service field for now.
        """
        return [format_cv_item(item) for item in article.get('anpa_category', [])]

    def _get_renditions(self, article):
        """Get renditions for article."""
        renditions = {}
        for name, rendition in article.get('renditions', {}).items():
            renditions[name] = self._format_rendition(rendition)
        return renditions

    def _format_rendition(self, rendition):
        """Format single rendition using fields whitelist."""
        return {field: rendition[field] for field in self.rendition_properties if field in rendition}
