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
from draftjs_exporter.html import HTML
from draftjs_exporter.constants import ENTITY_TYPES, INLINE_STYLES
from draftjs_exporter.defaults import STYLE_MAP
from draftjs_exporter.dom import DOM


logger = logging.getLogger(__name__)
DUMMY_RE = re.compile(r"</?dummy_tag>")

ANNOTATION = 'ANNOTATION'
MEDIA = 'MEDIA'
TABLE = 'TABLE'

ENTITY_RANGES = 'entityRanges'
INLINE_STYLE_RANGES = 'inlineStyleRanges'


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

    def __init__(self, editor, data=None):
        if data is None:
            data = {
                "key": str(uuid.uuid4()),
                "text": "",
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

    def replace_text(self, old, new):
        if not self.text:
            return
        if not old:
            raise ValueError("old is empty")
        start = 0
        while True:
            try:
                index = self.text.index(old, start)
                start = index + len(old)
                self.data['text'] = new.join([self.text[:index], self.text[start:]])
                for range_field in (ENTITY_RANGES, INLINE_STYLE_RANGES):
                    if self.data.get(range_field):
                        ranges = []
                        for range_ in self.data[range_field]:
                            range_end = range_['offset'] + range_['length']
                            if range_['offset'] > start:
                                # move ranges starting after replaced text
                                range_['offset'] += len(new) - len(old)
                                ranges.append(range_)
                            elif range_end <= index:
                                # keep ranges before replaced text
                                ranges.append(range_)
                            else:
                                # remove ranges overlapping with replaced text
                                if range_field == ENTITY_RANGES:
                                    self.entities.pop(range_["key"])
                                continue
                        self.data[range_field] = ranges
            except ValueError:
                break

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
        if 'fields_meta' in item:
            return Editor3Content(item, field)
        else:
            raise NotImplementedError("This is not an editor 3 item, EditorContent doesn't manage this")


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
            if v['data']['media'] == props['media'])

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
        # FIXME: Qumu hack is not handled yet
        div = DOM.create_element('div', {'class': 'embed-block'})
        embedded_html = DOM.parse_html(props['data']['html'])
        DOM.append_child(div, embedded_html)
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

    def __init__(self, item, field='body_html'):
        """
        :param item: item containing Draft.js ContentState
        :param field: field to manage, can be "body_html", "headline", etc.
        """
        self.item = item
        self.field = field
        data = item.get('fields_meta', {}).get(field, {})
        if not data:
            self.content_state = {}
        else:
            # if the field exist, draftjsState must exist too
            self.content_state = data['draftjsState'][0]
        self.blocks = BlockSequence(self)

        self.html_exporter = DraftJSHTMLExporter(self)

    @property
    def html(self):
        return self.html_exporter.render()

    @property
    def text(self):
        return '\n'.join([block.text for block in self.blocks])

    def get_next_entity_key(self):
        """Return a non existing key for entityMap"""
        return max((int(k) for k in self.content_state['entityMap'].keys()), default=-1) + 1

    def update_item(self, text=False):
        self.item[self.field] = self.text if text else self.html

    def create_block(self, block_type, *args, **kwargs):
        cls_name = "{}Block".format(block_type.capitalize())
        cls = globals()[cls_name]
        return cls(self, *args, **kwargs)

    def set_blocks(self, blocks):
        data = self.blocks[0].data.get('data')  # store internal data from first block
        self.content_state['blocks'] = [getattr(block, 'data', block) for block in blocks]
        self.blocks = BlockSequence(self)
        if not len(self.blocks):
            self.prepend('Unstyled')
        if not self.blocks[0].data.get('data'):
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
