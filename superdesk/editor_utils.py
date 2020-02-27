#!/usr/bin/env python3
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""This module contains tools to manage content for Superdesk editor"""

import re
import logging
import uuid
from textwrap import dedent
from collections.abc import MutableSequence

from flask import current_app as app

from draftjs_exporter.html import HTML
from draftjs_exporter.constants import ENTITY_TYPES, INLINE_STYLES, BLOCK_TYPES
from draftjs_exporter.defaults import STYLE_MAP, BLOCK_MAP
from draftjs_exporter.dom import DOM
from .etree import parse_html, to_string


logger = logging.getLogger(__name__)
DUMMY_RE = re.compile(r"</?dummy_tag>")

ANNOTATION = 'ANNOTATION'
MEDIA = 'MEDIA'
TABLE = 'TABLE'

EDITOR_STATE = 'draftjsState'
ENTITY_MAP = 'entityMap'
ENTITY_RANGES = 'entityRanges'
INLINE_STYLE_RANGES = 'inlineStyleRanges'

TAG_STYLE_MAP = {
    'i': INLINE_STYLES.ITALIC,
    'em': INLINE_STYLES.ITALIC,
    'b': INLINE_STYLES.BOLD,
    'strong': INLINE_STYLES.BOLD,
}

TAG_ENTITY_MAP = {
    'a': ENTITY_TYPES.LINK,
}


def get_field_content_state(item, field):
    try:
        return item['fields_meta'][field][EDITOR_STATE][0]
    except (KeyError, AttributeError):
        return None


def set_field_content_state(item, field, content_state):
    item.setdefault('fields_meta', {}).update({field: {EDITOR_STATE: [content_state]}})


class Entity:
    """Abstraction of a DraftJS entity"""

    def __init__(self, ranges, data):
        self.ranges = ranges
        self.data = data

    @property
    def key(self):
        return str(self.ranges['key'])

    @property
    def type(self):
        return self.data['type']

    @property
    def is_mutable(self):
        return self.data['mutability'] == 'MUTABLE'

    @property
    def content(self):
        return self.data['data']

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return "{mutable}{type} entity (key: {key})".format(
            mutable="mutable " if self.is_mutable else "",
            type=self.type,
            key=self.key,
        )


class EntitySequence(MutableSequence):

    def __init__(self, editor, block):
        self._ranges = block.data.setdefault('entityRanges', [])
        self._mapping = editor.content_state.setdefault('entityMap', {})

    def __getitem__(self, key):
        ranges = self._ranges[key]
        data = self._mapping[str(ranges['key'])]
        return Entity(ranges, data)

    def __setitem__(self, key, value):
        if not isinstance(value, Entity):
            raise TypeError("an Entity instance is expected")
        self._ranges[key] = value.ranges
        self._mapping[value.key] = value.data

    def __delitem__(self, key):
        entity_key = str(self._ranges[key]['key'])
        del self._ranges[key]
        del self._mapping[entity_key]

    def __len__(self):
        return len(self._ranges)

    def insert(self, index, value):
        if not isinstance(value, Entity):
            raise TypeError("an Entity instance is expected")
        self._ranges.insert(index, value.ranges)
        self._mapping[value.key] = value.data


class Block:
    """Abstraction of DraftJS block"""

    def __init__(self, editor, data=None, text=None):
        if data is None:
            data = {
                "key": str(uuid.uuid4()),
                "text": text or "",
                "type": "unstyled",
                "depth": 0,
                "inlineStyleRanges": [],
                "entityRanges": [],
                "data": {},
            }
        self.data = data
        self.entities = EntitySequence(editor, self)

    @property
    def depth(self):
        return self.data['depth']

    @property
    def type(self):
        return self.data['type']

    @property
    def text(self):
        return self.data.get('text')

    @property
    def key(self):
        return self.data.get('key')

    def __str__(self):
        return self.text

    def __repr__(self):
        return "{type} block with text {text!r} and {len_entities} entities".format(
            type=self.type, text=self.text, len_entities=len(self.entities))


class EmbedBlock(Block):

    def __init__(self, editor, html):
        """
        :param str html: raw HTML to embed
        """
        super().__init__(editor)
        self.data.update({
            "text": " ",
            "type": "atomic",
        })
        entity_data = {
            "type": "EMBED",
            "mutability": "MUTABLE",
            "data": {
                "data": {
                    "html": html,
                }
            },
        }
        entity = Entity(
            ranges={"offset": 0, "length": 1, "key": editor.get_next_entity_key()},
            data=entity_data,
        )
        self.entities.append(entity)


class UnstyledBlock(Block):
    def __init__(self, editor, text=None):
        super().__init__(editor)
        if text:
            self.data.update({"text": text})


class BlockSequence(MutableSequence):

    def __init__(self, editor):
        self.editor = editor
        self._blocks = editor.content_state.setdefault('blocks', {})

    def __getitem__(self, key):
        return Block(self.editor, self._blocks[key])

    def __setitem__(self, key, value):
        if not isinstance(value, Block):
            raise TypeError("a Block instance is expected")
        self._blocks[key] = value.data

    def __delitem__(self, key):
        del self._blocks[key]

    def __len__(self):
        return len(self._blocks)

    def insert(self, index, value):
        if not isinstance(value, Block):
            raise TypeError("a Block instance is expected")
        self._blocks.insert(index, value.data)


class EditorContent:
    """Base class to manage content from editors"""

    def __init__(self):
        raise RuntimeError("This class must not be instantiated directly, use create()")

    @staticmethod
    def create(item, field):
        """Factory for EditorContent"""
        return Editor3Content(item, field)


class DraftJSHTMLExporter:

    def __init__(self, content_editor):
        self.content_editor = content_editor
        # XXX: we need one exporter per DraftJSHTMLExporter because
        #      self.render_media needs to access "entityMap" from local
        #      instance. If MEDIA rendering changes in the future, exporter
        #      should be global for all DraftJSHTMLExporter instances
        self.exporter = HTML({
            'engine': DOM.LXML,
            'style_map': dict(STYLE_MAP, **{
                INLINE_STYLES.BOLD: 'b',
                INLINE_STYLES.ITALIC: 'i',
                INLINE_STYLES.FALLBACK: self.style_fallback,
            }),
            'entity_decorators': {
                ENTITY_TYPES.LINK: self.render_link,
                ENTITY_TYPES.HORIZONTAL_RULE: lambda props: DOM.create_element('hr'),
                ENTITY_TYPES.EMBED: self.render_embed,
                MEDIA: self.render_media,
                ANNOTATION: self.render_annotation,
                TABLE: self.render_table,
            },
        })

    @property
    def content_state(self):
        return self.content_editor.content_state

    def render(self):
        blocks = self.content_state['blocks']
        if not blocks:
            return ''
        if blocks and blocks[0]['text'].strip() == '' or blocks[-1]['text'].strip() == '':
            # first and last block may be empty due to client constraints, in this case
            # we must discard them during rendering
            content_state = self.content_state.copy()
            content_state['blocks'] = blocks = blocks[:]
            if blocks[0]['text'].strip() == '' and not blocks[0]['entityRanges']:
                del blocks[0]
            if blocks and blocks[-1]['text'].strip() == '' and not blocks[-1]['entityRanges']:
                del blocks[-1]
            html = self.exporter.render(content_state)
        else:
            html = self.exporter.render(self.content_state)
        # see render_media for details
        return DUMMY_RE.sub('', html)

    def render_annotation(self, props):
        return props['children']

    def render_media(self, props):
        media_props = props['media']
        media_type = media_props.get('type', 'picture')
        rendition = media_props['renditions'].get('original') or media_props['renditions']['viewImage']
        alt_text = media_props.get('alt_text') or ''
        desc = media_props.get('description_text')
        if media_type == 'picture':
            embed_type = "Image"
            elt = DOM.create_element('img', {'src': rendition['href'],
                                             'alt': alt_text}, props['children'])
        elif media_type == 'video':
            embed_type = "Video"
            elt = DOM.create_element('video', {'control': 'control',
                                               'src': rendition['href'],
                                               'alt': alt_text,
                                               'width': '100%',
                                               'height': '100%'}, props['children'])
        elif media_type == 'audio':
            embed_type = "Audio"
            elt = DOM.create_element('audio', {'control': 'control',
                                               'src': rendition['href'],
                                               'alt': alt_text,
                                               'width': '100%',
                                               'height': '100%'}, props['children'])
        else:
            logger.error("Invalid or not implemented media type: {media_type}".format(
                media_type=media_type))
            return None

        content = DOM.render(elt)

        if desc:
            content += "<figcaption>{}</figcaption>".format(desc)

        # we need to retrieve the key, there is not straightforward way to do it
        # so we find the key in entityMap with a corresponding value
        embed_key = next(
            k for k, v in self.content_state['entityMap'].items()
            if v['data'].get('media') == props['media'])

        # <dummy_tag> is needed for the comments, because a root node is necessary
        # it will be removed during rendering.
        embed = DOM.parse_html(dedent("""\
            <dummy_tag><!-- EMBED START {embed_type} {{id: "editor_{key}"}} -->
            <figure>{content}</figure>
            <!-- EMBED END {embed_type} {{id: "editor_{key}"}} --></dummy_tag>""").format(
            embed_type=embed_type,
            key=embed_key,
            content=content)
        )

        return embed

    def render_link(self, props):
        if 'url' in props:
            attribs = {'href': props['url']}
        else:
            link_data = props.get('link', {})
            if link_data.get('attachment'):
                attribs = {'data-attachment': link_data['attachment']}
            elif link_data.get('target'):
                attribs = {'href': link_data['href'], 'target': link_data['target']}
            else:
                attribs = {'href': link_data['href']}

        return DOM.create_element('a', attribs, props['children'])

    def render_embed(self, props):
        embed_pre_process = app.config.get('EMBED_PRE_PROCESS')
        if embed_pre_process:
            for callback in embed_pre_process:
                callback(props['data'])
        # we use superdesk.etree.parse_html instead of DOM.parse_html as the later modify the content
        # and we use directly the wrapping <div> returned with "content='html'". This works because
        # we use the lxml engine with DraftJSExporter.
        div = parse_html(props['data']['html'], content='html')
        div.set('class', 'embed-block')
        description = props.get('description')
        if description:
            p = DOM.create_element('p', {'class': 'embed-block__description'}, description)
            DOM.append_child(div, p)

        return div

    def render_table(self, props):
        num_cols = props['data']['numCols']
        num_rows = props['data']['numRows']
        with_header = props['data'].get('withHeader', False)
        cells = props['data']['cells']
        table = DOM.create_element('table')
        if with_header:
            start_row = 1
            thead = DOM.create_element('thead')
            DOM.append_child(table, thead)
            tr = DOM.create_element('tr')
            DOM.append_child(thead, tr)
            for col_idx in range(num_cols):
                th = DOM.create_element('th')
                DOM.append_child(tr, th)
                try:
                    content_state = cells[0][col_idx]
                except IndexError:
                    continue
                content = DOM.parse_html(self.exporter.render(content_state))
                if content.text or len(content):
                    DOM.append_child(th, content)
        else:
            start_row = 0

        if not with_header or num_rows > 1:
            tbody = DOM.create_element('tbody')
            DOM.append_child(table, tbody)

        for row_idx in range(start_row, num_rows):
            tr = DOM.create_element('tr')
            DOM.append_child(tbody, tr)
            for col_idx in range(num_cols):
                td = DOM.create_element('td')
                DOM.append_child(tr, td)
                try:
                    content_state = cells[row_idx][col_idx]
                except IndexError:
                    continue
                content = DOM.parse_html(self.exporter.render(content_state))
                if content.text or len(content):
                    DOM.append_child(td, content)

        return table

    def style_fallback(self, props):
        type_ = props['inline_style_range']['style']
        # we need to use fallback for annotations, has they have suffixes, it's
        # not only "ANNOTATION"
        if type_.startswith('ANNOTATION'):
            attribs = {"annotation-id": type_[11:]}
            return DOM.create_element('span', attribs, props['children'])
        else:
            logger.error("No style renderer for {type_!r}".format(type_=type_))


class Editor3Content(EditorContent):
    """Handle content for Superdesk Editor 3, using Draft.js ContentState

    see https://medium.com/@rajaraodv/how-draft-js-represents-rich-text-data-eeabb5f25cf2 for documentation
    on ContentState.
    """

    editor_version = 3
    HTML_EXPORTER = DraftJSHTMLExporter

    def __init__(self, item, field='body_html', is_html=True):
        """
        :param item: item containing Draft.js ContentState
        :param field: field to manage, can be "body_html", "headline", etc.
        :param is_html: boolean to indicate if the field is html or text field
        """
        self.item = item
        self.field = field
        self.is_html = is_html
        self.content_state = get_field_content_state(item, field)
        if not self.content_state:
            self._create_state_from_html(item.get(field))
        self.blocks = BlockSequence(self)
        self.html_exporter = DraftJSHTMLExporter(self)

    def _create_state_from_html(self, value=None):
        self.content_state = {
            'blocks': [],
            'entityMap': {},
        }

        if not value:
            return

        def create_entity(entity_type, data, mutability='MUTABLE'):
            key = len(self.content_state['entityMap'].keys())
            self.content_state['entityMap'][str(key)] = {
                'type': entity_type,
                'mutability': mutability,
                'data': data,
            }
            return key

        def create_atomic_block(entity_type, data):
            block = self.create_block('atomic', text=" ").data
            entity_key = create_entity(entity_type, data)
            block['entityRanges'] = [{'offset': 0, 'length': 1, 'key': entity_key}]
            block['inlineStyleRanges'] = []
            self.content_state['blocks'].append(block)

        if self.is_html:
            root = parse_html(value, 'html')
            for i, elem in enumerate(root):
                try:
                    block_type = next((key for key, val in BLOCK_MAP.items() if val == elem.tag))
                    depth = 0
                except StopIteration:
                    block_type = None
                    depth = 0
                    if elem.tag == 'figure':
                        try:
                            m = re.search(r'<!-- EMBED START (?:Image|Video) {id: "(.*)"}', str(root[i - 1]).strip())
                            media = self.item['associations'][m.group(1)]
                            create_atomic_block('MEDIA', {'media': media})
                        except (KeyError, IndexError, AttributeError):
                            create_atomic_block('EMBED', {'data': {'html': to_string(elem, method='html')}})
                        continue
                    elif elem.tag in ('ul', 'ol'):
                        pass  # generate block for each li
                    elif elem.text and '<!-- EMBED' in str(elem):
                        continue
                    elif elem.tag == 'table':
                        data = {'numCols': 0, 'numRows': 0, 'withHeader': False, 'cells': {}}
                        for row, tr in enumerate(elem.iter('tr')):
                            data['numRows'] += 1
                            data['cells'][row] = {}
                            if row == 0 and len(tr):
                                data['numCols'] = len(tr)
                                data['withHeader'] = tr[0].tag == 'th'
                            for col, td in enumerate(tr):
                                data['cells'][row][col] = {
                                    'blocks': [
                                        self.create_block('unstyled', text="".join(td.itertext())).data,
                                    ],
                                    'entityMap': {},
                                }
                        create_atomic_block('TABLE', {'data': data})
                        continue
                    elif elem.tag == 'div':
                        html = ''.join([to_string(child, method='html') for child in elem])
                        if html.startswith('<html><head>'):
                            html = re.sub(
                                r'<\/head><\/html>',
                                '',
                                html.replace('<html><head>', '', 1),
                            )
                        create_atomic_block('EMBED', {'data': {'html': html}})
                        continue
                    else:
                        logger.warning('ignore block %s', str(elem.tag))
                        continue
                block_text = elem.text or ""
                inline_style_ranges = []
                entity_ranges = []
                for child in elem:
                    child_text = "".join(child.itertext())

                    if child.tag in TAG_STYLE_MAP:
                        inline_style_ranges.append({
                            'offset': len(block_text),
                            'length': len(child_text),
                            'style': TAG_STYLE_MAP[child.tag],
                        })

                    if child.tag in TAG_ENTITY_MAP:
                        if not child_text:
                            child_text = " "  # must be non-empty
                        if child.tag == 'a':
                            data = {'link': {'href': child.attrib.get('href'), 'target': child.attrib.get('target')}}
                        else:
                            data = {}
                        entity_key = create_entity(TAG_ENTITY_MAP[child.tag], data)
                        entity_ranges.append({'offset': len(block_text), 'length': len(child_text), 'key': entity_key})

                    if child.tag == 'li':
                        child_type = BLOCK_TYPES.UNORDERED_LIST_ITEM if elem.tag == 'ul' \
                            else BLOCK_TYPES.ORDERED_LIST_ITEM
                        block = self.create_block(child_type, text=child_text).data
                        block.update(depth=depth)
                        self.content_state['blocks'].append(block)

                    block_text += child_text

                    if child.tail and child.tail.strip():
                        block_text += child.tail

                if elem.tail and elem.tail.strip():
                    block_text += elem.tail

                if block_type:  # no block type for ul/ol
                    block = self.create_block(block_type, text=block_text).data
                    block['inlineStyleRanges'] = inline_style_ranges
                    block['entityRanges'] = entity_ranges
                    self.content_state['blocks'].append(block)
        else:
            for line in value.split('\n'):
                self.content_state['blocks'].append(self.create_block(BLOCK_TYPES.UNSTYLED, text=line).data)

    @property
    def html(self):
        return self.html_exporter.render()

    @property
    def text(self):
        return '\n'.join([block.text for block in self.blocks])

    def get_next_entity_key(self):
        """Return a non existing key for entityMap"""
        return max((int(k) for k in self.content_state['entityMap'].keys()), default=-1) + 1

    def update_item(self):
        self.item[self.field] = self.html if self.is_html else self.text
        set_field_content_state(self.item, self.field, self.content_state)

    def create_block(self, block_type, *args, **kwargs):
        cls_name = "{}Block".format(block_type.capitalize())
        if cls_name in globals():
            cls = globals()[cls_name]
            return cls(self, *args, **kwargs)
        else:
            block = Block(self, *args, **kwargs)
            block.data['type'] = block_type
            return block

    def set_blocks(self, blocks):
        try:
            data = self.blocks[0].data.get('data')  # store internal data from first block
        except IndexError:
            data = {}
        self.content_state['blocks'] = [getattr(block, 'data', block) for block in blocks]
        self.blocks = BlockSequence(self)
        if not len(self.blocks):
            self.prepend('Unstyled')
        if not self.blocks[0].data.get('data') and data:
            self.blocks[0].data['data'] = data

    def prepend(self, block_type, *args, **kwargs):
        """Shortcut to prepend a block from its type"""
        block = self.create_block(block_type, *args, **kwargs)
        self.prepend_block(block)
        return block

    def prepend_block(self, block):
        # first block may be empty, this is a client constraint. In this case,
        # we prepend our block after it
        if self.blocks and not self.blocks[0].text.strip():
            index = 1
        else:
            index = 0
        self.blocks.insert(index, block)


def _replace_text(content_state, old, new):
    if not old:
        return
    for block in content_state['blocks']:
        if block.get('type') == 'atomic':
            entity = content_state[ENTITY_MAP][str(block[ENTITY_RANGES][0]['key'])]
            if entity['type'] == 'TABLE':
                cells = entity['data']['data']['cells']
                for row in cells.values():
                    for cell in row.values():
                        _replace_text(cell, old, new)
            continue
        if not block.get('text'):
            continue
        end = 0
        while True:
            try:
                index = block['text'].index(old, end)
                end = index + len(old)
                block['text'] = new.join([block['text'][:index], block['text'][end:]])
                for range_field in (ENTITY_RANGES, INLINE_STYLE_RANGES):
                    if block.get(range_field):
                        ranges = []
                        for range_ in block[range_field]:
                            range_end = range_['offset'] + range_['length']
                            if range_['offset'] > end:  # starting after replaced, move it
                                range_['offset'] += len(new) - len(old)
                                ranges.append(range_)
                            elif range_end <= index:  # starting before replaced text, keep it
                                ranges.append(range_)
                            elif range_['offset'] <= index and range_end >= end:  # contain the text, fix length
                                range_['length'] += len(new) - len(old)
                                ranges.append(range_)
                            else:
                                # remove ranges overlapping with replaced text
                                if range_field == ENTITY_RANGES:
                                    content_state['entityMap'].pop(str(range_["key"]))
                                continue
                        block[range_field] = ranges
            except ValueError:
                break


def replace_text(item, field, old, new, is_html=True):
    """Replace all occurences of old replaced with new.

    It won't replace it in atomic blocks and embeds,
    only text blocks, headings, tables, ul/ol.
    """
    editor = Editor3Content(item, field, is_html)
    _replace_text(editor.content_state, old, new)
    editor.update_item()


def filter_blocks(item, field, filter, is_html=True):
    """Filter content blocks for field.

    It will keep only blocks for which filter returns True.
    """
    editor = Editor3Content(item, field, is_html)
    blocks = []
    for block in editor.blocks:
        if filter(block):
            blocks.append(block)
    editor.set_blocks(blocks)
    editor.update_item()
