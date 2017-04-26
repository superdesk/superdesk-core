# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""NINJS formatter for Superdesk

.. versionadded:: 1.8
    Added *source* field.

.. versionadded:: 1.7
    Added *ednote* field.
    Added *signal* field.
    Added *genre* field.

.. versionchanged:: 1.7
    Fixed copyrightholder/copyrightnotice handling to be consistent with newsml.
    Fixed place property qcode should be code.
    Output profile name instead of _id in profile field.

.. versionadded:: 1.6
    Added *evolvedfrom* field to ninjs output.

"""


import json
import superdesk

from eve.utils import config
from superdesk.publish.formatters import Formatter
from superdesk.errors import FormatterError
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, EMBARGO, GUID_FIELD, ASSOCIATIONS
from superdesk.metadata.packages import RESIDREF, GROUP_ID, GROUPS, ROOT_GROUP, REFS
from superdesk.utils import json_serialize_datetime_objectId
from superdesk.media.renditions import get_renditions_spec
from apps.archive.common import get_utc_schedule
from superdesk.etree import get_text


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
    The schema we use for the ninjs format is an extension
    of `the standard ninjs schema <http://www.iptc.org/std/ninjs/ninjs-schema_1.1.json>`_.

    *Changes from ninjs schema*:

    * ``uri`` was replaced by ``guid``: ``uri`` should be the resource identifier on the web
        but since the item was not published yet it can't be determined at this point
    * added ``priority`` field
    * added ``service`` field
    * added ``slugline`` field
    * added ``keywords`` field
    * added ``evolvedfrom`` field
    * added ``source`` field

    Associations dictionary may contain entire items like
    in `ninjs example <http://dev.iptc.org/ninjs-Examples-3>`_ or just the item ``guid``
    and ``type``. In the latest case the items are sent separately before the package item.
    """

    direct_copy_properties = ('versioncreated', 'usageterms', 'language', 'headline', 'copyrightnotice',
                              'urgency', 'pubstatus', 'mimetype', 'copyrightholder', 'ednote',
                              'body_text', 'body_html', 'slugline', 'keywords',
                              'firstcreated', 'source')

    rendition_properties = ('href', 'width', 'height', 'mimetype', 'poi', 'media')
    vidible_fields = {field: field for field in rendition_properties}
    vidible_fields.update({
        'url': 'href',
        'duration': 'duration',
        'mimeType': 'mimetype',
        'size': 'size',
    })

    def __init__(self):
        self.format_type = 'ninjs'
        self.can_preview = True
        self.can_export = True

    def format(self, article, subscriber, codes=None):
        try:
            pub_seq_num = superdesk.get_resource_service('subscribers').generate_sequence_number(subscriber)

            ninjs = self._transform_to_ninjs(article, subscriber)
            return [(pub_seq_num, json.dumps(ninjs, default=json_serialize_datetime_objectId))]
        except Exception as ex:
            raise FormatterError.ninjsFormatterError(ex, subscriber)

    def _transform_to_ninjs(self, article, subscriber, recursive=True):
        ninjs = {
            'guid': article.get(GUID_FIELD, article.get('uri')),
            'version': str(article.get(config.VERSION, 1)),
            'type': self._get_type(article)
        }

        if article.get('byline'):
            ninjs['byline'] = article['byline']

        located = article.get('dateline', {}).get('located', {})
        if located:
            ninjs['located'] = located.get('city', '')

        for copy_property in self.direct_copy_properties:
            if article.get(copy_property) is not None:
                ninjs[copy_property] = article[copy_property]

        if 'body_text' not in article and 'alt_text' in article:
            ninjs['body_text'] = article['alt_text']

        if 'title' in article:
            ninjs['headline'] = article['title']

        if article.get('body_html'):
            ninjs['body_html'] = self.append_body_footer(article)

        if article.get('description'):
            ninjs['description_html'] = self.append_body_footer(article)

        if article.get('place'):
            ninjs['place'] = self._format_qcodes(article['place'])

        if article.get('profile'):
            ninjs['profile'] = self._format_profile(article['profile'])

        if recursive:
            if article[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
                ninjs[ASSOCIATIONS] = self._get_associations(article, subscriber)
                if article.get(ASSOCIATIONS):
                    ninjs[ASSOCIATIONS].update(self._format_related(article, subscriber))
            elif article.get(ASSOCIATIONS):
                ninjs[ASSOCIATIONS] = self._format_related(article, subscriber)
        elif article.get(ASSOCIATIONS):
            ninjs[ASSOCIATIONS] = self._format_related(article, subscriber)

        if article.get(EMBARGO):
            ninjs['embargoed'] = get_utc_schedule(article, EMBARGO).isoformat()

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
        elif 'url' in article:
            ninjs['renditions'] = self._generate_renditions(article)

        # SDPA-317
        if article.get('abstract'):
            abstract = article.get('abstract', '')
            ninjs['description_html'] = abstract
            ninjs['description_text'] = get_text(abstract)
        elif article.get('description_text'):
            ninjs['description_text'] = article.get('description_text')

        if article.get('company_codes'):
            ninjs['organisation'] = [{'name': c.get('name', ''), 'rel': 'Securities Identifier',
                                      'symbols': [{'ticker': c.get('qcode', ''),
                                                   'exchange': c.get('security_exchange', '')}]}
                                     for c in article['company_codes']]
        elif 'company' in article:
            ninjs['organisation'] = [{'name': article['company']}]

        if article.get('rewrite_of'):
            ninjs['evolvedfrom'] = article['rewrite_of']

        if not ninjs.get('copyrightholder') and not ninjs.get('copyrightnotice') and not ninjs.get('usageterms'):
            ninjs.update(superdesk.get_resource_service('vocabularies').get_rightsinfo(article))

        if article.get('genre'):
            ninjs['genre'] = self._format_qcodes(article['genre'])

        if article.get('flags', {}).get('marked_for_legal'):
            ninjs['signal'] = self._format_signal_cwarn()

        return ninjs

    def _generate_renditions(self, article):
        """
        For associated items that have custom structure generate renditions based on the item `custom properties.
        """
        renditions = {'original': {}}
        for orig_field, dest_field in self.vidible_fields.items():
            if orig_field in article:
                renditions['original'][dest_field] = article[orig_field]
        if 'thumbnail' in article:
            renditions['thumbnail'] = {'href': article['thumbnail']}
        return renditions

    def can_format(self, format_type, article):
        return format_type == self.format_type

    def _get_type(self, article):
        if article[ITEM_TYPE] == CONTENT_TYPE.PREFORMATTED:
            return CONTENT_TYPE.TEXT
        return article[ITEM_TYPE]

    def _get_associations(self, article, subscriber):
        """Create associations dict for package groups."""
        associations = dict()
        for group in article.get(GROUPS, []):
            if group[GROUP_ID] == ROOT_GROUP:
                continue

            group_items = []
            for ref in group[REFS]:
                if RESIDREF in ref:
                    item = {}
                    item['guid'] = ref[RESIDREF]
                    item[ITEM_TYPE] = ref.get(ITEM_TYPE, 'text')
                    if ref.get('package_item'):
                        item.update(self._transform_to_ninjs(ref['package_item'], subscriber, recursive=False))
                    group_items.append(item)
            if len(group_items) == 1:
                associations[group[GROUP_ID]] = group_items[0]
            elif len(group_items) > 1:
                for index in range(0, len(group_items)):
                    associations[group[GROUP_ID] + '-' + str(index)] = group_items[index]
        return associations

    def _format_related(self, article, subscriber):
        """Format all associated items for simple items (not packages)."""
        associations = {}
        for key, item in (article.get(ASSOCIATIONS) or {}).items():
            if item:
                associations[key] = self._transform_to_ninjs(item, subscriber)
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
        # get the actual article's renditions
        actual_renditions = article.get('renditions', {})
        # renditions list that we want to publish
        if article['type'] is 'picture':
            renditions_to_publish = ['original'] + list(get_renditions_spec(without_internal_renditions=True).keys())
            # filter renditions and keep only the ones we want to publish
            actual_renditions = {name: actual_renditions[name] for name in renditions_to_publish
                                 if name in actual_renditions}
        # format renditions to Ninjs
        renditions = {}
        for name, rendition in actual_renditions.items():
            renditions[name] = self._format_rendition(rendition)
        return renditions

    def _format_rendition(self, rendition):
        """Format single rendition using fields whitelist."""
        return {field: rendition[field] for field in self.rendition_properties if field in rendition}

    def _format_qcodes(self, items):
        return [{'name': item.get('name'), 'code': item.get('qcode')} for item in items]

    def _format_profile(self, profile):
        return superdesk.get_resource_service('content_types').get_output_name(profile)

    def _format_signal_cwarn(self):
        return [{'name': 'Content Warning', 'code': 'cwarn', 'scheme': 'http://cv.iptc.org/newscodes/signal/'}]

    def export(self, item):
        if self.can_format(self.format_type, item):
            sequence, formatted_doc = self.format(item, {'_id': '0'}, None)[0]
            return formatted_doc.replace('\'\'', '\'')
        else:
            raise Exception()
