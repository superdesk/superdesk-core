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
import logging

from eve.utils import config
from superdesk.publish.formatters import Formatter
from superdesk.errors import FormatterError
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, EMBARGO, GUID_FIELD, ASSOCIATIONS
from superdesk.metadata.packages import RESIDREF, GROUP_ID, GROUPS, ROOT_GROUP, REFS
from superdesk.utils import json_serialize_datetime_objectId
from superdesk.media.renditions import get_renditions_spec
from apps.archive.common import get_utc_schedule
from superdesk import text_utils
from draftjs_exporter.html import HTML
from draftjs_exporter.dom import DOM
from draftjs_exporter.constants import ENTITY_TYPES
from superdesk import etree as sd_etree
from functools import partial

logger = logging.getLogger(__name__)

ANNOTATION = 'ANNOTATION'
MEDIA = 'MEDIA'
TABLE = 'TABLE'


def filter_empty_vals(data):
    """Filter out `None` values from a given dict."""
    return dict(filter(lambda x: x[1], data.items()))


def get_locale_name(item, language):
    try:
        return item['translations']['name'][language]
    except (KeyError, TypeError):
        return item.get('name', '')


def format_cv_item(item, language):
    """Format item from controlled vocabulary for output."""
    return filter_empty_vals({
        'code': item.get('qcode'),
        'name': get_locale_name(item, language),
        'scheme': item.get('scheme')
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
                              'firstcreated', 'firstpublished', 'source', 'extra')

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

        if article.get('editor_state'):
            self._parse_editor_state(article, ninjs)

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
            ninjs['place'] = self._format_place(article)

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
        if 'abstract' in article:
            abstract = article.get('abstract', '')
            ninjs['description_html'] = abstract
            ninjs['description_text'] = text_utils.get_text(abstract)
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

        if 'genre' in article:
            ninjs['genre'] = self._get_genre(article)

        if article.get('flags', {}).get('marked_for_legal'):
            ninjs['signal'] = self._format_signal_cwarn()

        if article.get('attachments'):
            ninjs['attachments'] = self._format_attachments(article)

        if ninjs['type'] == CONTENT_TYPE.TEXT and ('body_html' in ninjs or 'body_text' in ninjs):
            if 'body_html' in ninjs:
                body_html = ninjs['body_html']
                word_count = text_utils.get_word_count(body_html)
                char_count = text_utils.get_char_count(body_html)
                readtime = text_utils.get_reading_time(body_html, word_count, article.get('language'))
            else:
                body_text = ninjs['body_text']
                word_count = text_utils.get_text_word_count(body_text)
                char_count = len(body_text)
                readtime = text_utils.get_reading_time(body_text, word_count, article.get('language'))
            ninjs['charcount'] = char_count
            ninjs['wordcount'] = word_count
            ninjs['readtime'] = readtime

        if article.get('authors'):
            ninjs['authors'] = self._format_authors(article)

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
                    if 'label' in ref:
                        item['label'] = ref.get('label')
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

    def _get_genre(self, article):
        lang = article.get('language', '')
        return [format_cv_item(item, lang) for item in article['genre']]

    def _get_subject(self, article):
        """Get subject list for article."""
        return [format_cv_item(item, article.get('language', '')) for item in article.get('subject', [])]

    def _get_service(self, article):
        """Get service list for article.

        It's using `anpa_category` to populate service field for now.
        """
        return [format_cv_item(item, article.get('language', '')) for item in article.get('anpa_category', [])]

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

    def _format_place(self, article):
        vocabularies_service = superdesk.get_resource_service('vocabularies')
        locator_map = vocabularies_service.find_one(req=None, _id='locators')
        if locator_map and 'items' in locator_map:
            locator_map['items'] = vocabularies_service.get_locale_vocabulary(
                locator_map.get('items'), article.get('language'))

        def get_label(item):
            if locator_map:
                locators = [l for l in locator_map.get('items', []) if l['qcode'] == item.get('qcode')]
                if locators and len(locators) == 1:
                    return locators[0].get('state') or \
                        locators[0].get('country') or \
                        locators[0].get('world_region') or \
                        locators[0].get('group')
            return item.get('name')

        return [{'name': get_label(item), 'code': item.get('qcode')} for item in article['place']]

    def _format_profile(self, profile):
        return superdesk.get_resource_service('content_types').get_output_name(profile)

    def _format_signal_cwarn(self):
        return [{'name': 'Content Warning', 'code': 'cwarn', 'scheme': 'http://cv.iptc.org/newscodes/signal/'}]

    def _format_attachments(self, article):
        output = []
        attachments_service = superdesk.get_resource_service('attachments')
        for attachment_ref in article['attachments']:
            attachment = attachments_service.find_one(req=None, _id=attachment_ref['attachment'])
            output.append({
                'id': str(attachment['_id']),
                'title': attachment['title'],
                'description': attachment['description'],
                'filename': attachment['filename'],
                'mimetype': attachment['mimetype'],
                'length': attachment.get('length'),
                'media': str(attachment['media']),
                'href': '/assets/{}'.format(str(attachment['media'])),
            })
        return output

    def _format_authors(self, article):
        users_service = superdesk.get_resource_service('users')
        vocabularies_service = superdesk.get_resource_service('vocabularies')
        job_titles_voc = vocabularies_service.find_one(None, _id='job_titles')
        if job_titles_voc and 'items' in job_titles_voc:
            job_titles_voc['items'] = vocabularies_service.get_locale_vocabulary(
                job_titles_voc.get('items'), article.get('language'))
        job_titles_map = {v['qcode']: v['name'] for v in job_titles_voc['items']} if job_titles_voc is not None else {}

        authors = []
        for author in article['authors']:
            try:
                user_id = author['parent']
            except KeyError:
                # XXX: in some older items, parent may be missing, we try to find user with name in this case
                try:
                    user = next(users_service.find({'display_name': author['name']}))
                except (StopIteration, KeyError):
                    logger.warn("unknown user")
                    user = {}
            else:
                try:
                    user = next(users_service.find({'_id': user_id}))
                except StopIteration:
                    logger.warn("unknown user: {user_id}".format(user_id=user_id))
                    user = {}

            author = {
                "name": user.get('display_name', author.get('name', '')),
                "role": author['role'],
                "biography": user.get('biography', ''),
            }

            if user.get('picture_url'):
                author['avatar_url'] = user['picture_url']

            job_title_qcode = user.get('job_title')
            if job_title_qcode is not None:
                author['jobtitle'] = {'qcode': job_title_qcode,
                                      'name': job_titles_map.get(job_title_qcode, '')}

            authors.append(author)
        return authors

    def _render_annotation(self, props):
        return DOM.create_element('span', {'annotation-id': props['id']}, props['children'])

    def _render_media(self, props):
        media_props = props['media']
        if media_props.get('type', 'picture') == 'picture':
            elt = DOM.create_element('img', {'src': media_props['renditions']['original']['href'],
                                             'alt': media_props.get('alt_text')}, props['children'])
        else:
            elt = DOM.create_element('video', {'control': 'control',
                                               'src': media_props['renditions']['original']['href'],
                                               'alt': media_props.get('alt_text'),
                                               'width': '100%',
                                               'height': '100%'}, props['children'])
        desc = DOM.create_element('span', {'class': 'media-block__description'}, media_props.get('description_text'))
        return DOM.create_element('div', {'class': 'media-block'}, [elt, desc])

    def _render_link(self, props):
        return DOM.create_element('a', {'href': props.get('link', {}).get('href', '')}, props['children'])

    def _render_embed(self, embeds, props):
        try:
            return embeds.pop(0)
        except IndexError:
            return ""

    def _render_table(self, props):
        # This code just fix the crash when the text contains tables. It will be fixed by processing
        # of annotation on frontend
        td = DOM.create_element('td', {}, 'Table not supported')
        tr = DOM.create_element('tr', {}, td)
        return DOM.create_element('table', {}, tr)

    def _parse_editor_state(self, article, ninjs):
        """Parse editor_state (DraftJs internals) to retrieve annotations

        body_html will be rewritten with HTML generated from DraftJS representation
        and annotation will be included in <span> elements
        :param article: item to modify, must contain "editor_state" data
        :param ninjs: ninjs item which will be formatted
        """
        blocks = article['editor_state'][0]['blocks']

        blocks_map = {}
        ann_idx = 0
        data = {}
        body_html_elt = sd_etree.parse_html(article['body_html'], 'html')
        embeds = body_html_elt.xpath('//div[@class="embed-block"]')
        config = {
            'engine': 'lxml',
            'entity_decorators': {
                ENTITY_TYPES.LINK: self._render_link,
                ENTITY_TYPES.HORIZONTAL_RULE: lambda props: DOM.create_element('hr'),
                ENTITY_TYPES.EMBED: partial(self._render_embed, embeds),
                MEDIA: self._render_media,
                ANNOTATION: self._render_annotation,
                TABLE: self._render_table,
            }
        }

        renderer = HTML(config)

        for block in blocks:
            blocks_map[block['key']] = block
            data.update(block['data'])

        # we sort data keys to have consistent annotations ids
        for key in sorted(data):
            data_block = data[key]
            if data_block['type'] == ANNOTATION:
                ninjs.setdefault('annotations', []).append(
                    {'id': ann_idx,
                     'type': data_block['annotationType'],
                     'body': renderer.render(json.loads(data_block['msg']))})
                entity_key = '_annotation_{}'.format(ann_idx)
                article['editor_state'][0]['entityMap'][entity_key] = {
                    'type': ANNOTATION,
                    'data': {'id': ann_idx}}
                ann_idx += 1
                selection = json.loads(key)
                if selection['isBackward']:
                    first, second = 'focus', 'anchor'
                else:
                    first, second = 'anchor', 'focus'
                first_key = selection[first + 'Key']
                second_key = selection[second + 'Key']
                first_offset = selection[first + 'Offset']
                second_offset = selection[second + 'Offset']
                # we want to style annotation with <span>, so we put them as entities
                if first_key == second_key:
                    # selection is done in a single block
                    annotated_block = blocks_map[first_key]
                    annotated_block.setdefault('entityRanges', []).append(
                        {'key': entity_key,
                         'offset': first_offset,
                         'length': second_offset - first_offset})
                else:
                    # selection is done on multiple blocks, we have to select them
                    started = False
                    for block in blocks:
                        if block['key'] == first_key:
                            started = True
                            block.setdefault('entityRanges', []).append(
                                {'key': entity_key,
                                 'offset': first_offset,
                                 'length': len(block['text']) - first_offset})
                        elif started:
                            inline = {'key': entity_key, 'offset': 0}
                            block.setdefault('entityRanges', []).append(inline)
                            if block['key'] == second_key:
                                # last block, we end the annotation here
                                inline['length'] = second_offset
                                break
                            else:
                                # intermediate block, we annotate it whole
                                inline['length'] = len(block['text'])
        # HTML rendering
        # now we have annotation ready, we can render HTML
        article['body_html'] = renderer.render(article['editor_state'][0])

    def export(self, item):
        if self.can_format(self.format_type, item):
            sequence, formatted_doc = self.format(item, {'_id': '0'}, None)[0]
            return formatted_doc.replace('\'\'', '\'')
        else:
            raise Exception()
