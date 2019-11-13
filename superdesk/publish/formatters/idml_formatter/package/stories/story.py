from lxml import etree

from ..base import BasePackageElement


class Story(BasePackageElement):
    """
    Story which represents `p`, `h1`, `h2`, `h3`, `h4`, `h5`, `h6`, `blockquote`, `pre`, `headline`, `byline` html tags.

    As Adobe's idml specification explains:
    ``
    A story, or “text flow” is the basic text container in an InDesign document;
    all text exists inside stories. Stories are associated with at least one text frame or text path,
    and can span any number of linked text frames or text paths in a document.
    ``
    """

    STORY_DEFAULTS = {
        'AppliedNamedGrid': 'n',
        'AppliedTOCStyle': 'n',
        'TrackChanges': 'false',
        'StoryTitle': '$ID/'
    }
    STORYPREFERENCE_DEFAULTS = {
        'OpticalMarginAlignment': 'false',
        'OpticalMarginSize': '12',
        'FrameType': 'TextFrameType',
        'StoryOrientation': 'Horizontal',
        'StoryDirection': 'LeftToRightDirection'
    }
    HYPERLINKTEXTSOURCE_DEFAULTS = {
        'Hidden': 'false',
        'AppliedCharacterStyle': 'CharacterStyle/$ID/Hyperlink'
    }
    PARAGRAPHSTYLERANGE_DEFAULTS = {
        'AppliedParagraphStyle': 'ParagraphStyle/$ID/NormalParagraphStyle'
    }
    CHARACTERSTYLERANGE_DEFAULTS = {
        'AppliedCharacterStyle': 'CharacterStyle/$ID/[No character style]',
    }
    BLOCK_TAGS_MAPPING = {
        'p': {
            'markup_tag': 'NormalParagraph',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Paragraphs%3aNormalParagraph'
            },
        },
        'blockquote': {
            'markup_tag': 'Blockquote',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Paragraphs%3aBlockquote'
            },
        },
        'pre': {
            'markup_tag': 'Preformatted',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Paragraphs%3aPreformatted'
            },
        },
        'h1': {
            'markup_tag': 'Heading1',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Headings%3aHeading1'
            },
        },
        'h2': {
            'markup_tag': 'Heading2',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Headings%3aHeading2'
            },
        },
        'h3': {
            'markup_tag': 'Heading3',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Headings%3aHeading3'
            },
        },
        'h4': {
            'markup_tag': 'Heading4',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Headings%3aHeading4'
            },
        },
        'h5': {
            'markup_tag': 'Heading5',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Headings%3aHeading5'
            },
        },
        'h6': {
            'markup_tag': 'Heading6',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Headings%3aHeading6'
            },
        },
        'table': {
            'markup_tag': 'Table',
            'Table': {
                'AppliedTableStyle': 'TableStyle/$ID/NormalTable'
            },
        },
        'ul': {
            'markup_tag': 'UnorderedList',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Lists%3aUnorderedList',
                'BulletsAndNumberingListType': 'BulletList',
            },
        },
        'ol': {
            'markup_tag': 'OrderedList',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Lists%3aOrderedList',
                'BulletsAndNumberingListType': 'NumberedList',
            },
        },
        # custom
        'headline': {
            'markup_tag': 'Headline',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Custom%3aHeadline'
            },
        },
        'byline': {
            'markup_tag': 'Byline',
            'ParagraphStyleRange': {
                'AppliedParagraphStyle': 'ParagraphStyle/Custom%3aByline'
            },
        },
    }
    INLINE_TAGS_MAPPING = {
        'b': [
            {
                'attribute': 'FontStyle',
                'value': 'Bold',
                'appendable': True
            }
        ],
        'i': [
            {
                'attribute': 'FontStyle',
                'value': 'Italic',
                'appendable': True
            }
        ],
        'u': [
            {
                'attribute': 'Underline',
                'value': 'true',
                'appendable': False
            }
        ],
        's': [
            {
                'attribute': 'StrikeThru',
                'value': 'true',
                'appendable': False
            }
        ],
        'sub': [
            {
                'attribute': 'Position',
                'value': 'Subscript',
                'appendable': False
            }
        ],
        'sup': [
            {
                'attribute': 'Position',
                'value': 'Superscript',
                'appendable': False
            }
        ],
        'a': [
            {
                'attribute': 'AppliedCharacterStyle',
                'value': 'CharacterStyle/$ID/Hyperlink',
                'appendable': False
            }
        ]
    }

    def __init__(self, self_id, element, attributes=None, markup_tag=None):
        self.self_id = self_id
        self._element = element
        self._markup_tag = markup_tag
        self.links = []
        super().__init__(attributes)

    @property
    def filename(self):
        """
        Filename inside IDML package.
        Used as a filename for a file inside zip container.
        :return str: filename
        """
        return 'Stories/Story_{}.xml'.format(self.self_id)

    def _build_etree(self):
        self._etree = etree.Element(
            etree.QName(self.XMLNS_IDPKG, 'Story'),
            nsmap={'idPkg': self.XMLNS_IDPKG}
        )
        self._etree.set('DOMVersion', self.DOM_VERSION)
        self._add_story()

    def _add_story(self):
        """
        Create <Story..> tag
        :return lxml.etree: Story etree instance
        """
        # merge Story attributes
        story_attributes = self.merge_attributes(
            self.STORY_DEFAULTS,
            self._attributes.get('Story', {})
        )
        story_attributes.update({'Self': self.self_id})
        # Story
        story = etree.SubElement(
            self._etree,
            'Story',
            attrib=story_attributes
        )
        # StoryPreference
        etree.SubElement(
            story,
            'StoryPreference',
            attrib=self.merge_attributes(
                self.STORYPREFERENCE_DEFAULTS,
                self._attributes.get('StoryPreference', {})
            )
        )

        if self._markup_tag:
            # XMLElement to tag a story
            paragraphstylerange_container = etree.SubElement(
                story,
                'XMLElement',
                attrib={
                    'Self': '{}_{}'.format(self.self_id, self._markup_tag.lower()),
                    'XMLContent': self.self_id,
                    'MarkupTag': 'XMLTag/{}'.format(self._markup_tag)
                }
            )
        else:
            paragraphstylerange_container = story

        # ParagraphStyleRange
        paragraphstylerange = etree.SubElement(
            paragraphstylerange_container,
            'ParagraphStyleRange',
            attrib=self.merge_attributes(
                self.PARAGRAPHSTYLERANGE_DEFAULTS,
                self._attributes.get('ParagraphStyleRange', {})
            )
        )

        paragraphstylerange[:] = self._handle_inline_tags(self._element)

        return story

    def _handle_inline_tags(self, element):
        """
        Convert html element's inline style to idml representation.
        :param lxml.etree element: html element
        :return list: list of CharacterStyleRange lxml.etree instances
        """
        element_dict = self._etree_element_to_dict(element)
        return self._create_characterstylerange_recursive(element_dict)

    def _etree_element_to_dict(self, element, parents=None):
        """
        Converts html element to dict.
        Example:
            `<p>normal <b>bold <u>bold-unerline</u> bold</b> normal</p>`
            will be converted to:
            ``
            {
                'attrib': {},
                'childs': (
                    {
                        'attrib': {},
                        'childs': (
                            {
                                'attrib': {},
                                'childs': (),
                                'parents': ('p', 'b'),
                                'tag': 'u',
                                'tail': ' bold',
                                'text': 'bold-unerline',
                            },
                        ),
                        'parents': ('p', ),
                        'tag': 'b',
                        'tail': ' normal',
                        'text': 'bold ',
                    },
                ),
                'parents': (),
                'tag': 'p',
                'tail': None,
                'text': 'normal ',
            }
            ``
        :param lxml.etree element: html element
        :param list parents: list of parent tags
        :return dict: dictionary

        """
        if not parents:
            parents = []

        element_dict = {
            'tag': element.tag,
            'attrib': element.attrib,
            'parents': tuple(parents),
            'text': element.text,
            'tail': element.tail
        }
        parents.append(element.tag)
        element_dict['childs'] = tuple(
            self._etree_element_to_dict(
                child,
                list(parents)
            ) for child in element.iterchildren()
        )

        return element_dict

    def _create_characterstylerange_recursive(self, element_dict, tail=False):
        """
        Create CharacterStyleRange(s) recursively.
        Example:
        ``
        <ParagraphStyleRange ...>
        <CharacterStyleRange AppliedCharacterStyle="..." FontStyle="Bold">
          <Content>Curabitur </Content>
        </CharacterStyleRange>
        <CharacterStyleRange AppliedCharacterStyle="..." FontStyle="Bold Italic">
          <Content>arcu erat</Content>
        </CharacterStyleRange>
        <CharacterStyleRange AppliedCharacterStyle="..." FontStyle="Bold">
          <Content>, accumsan </Content>
        </CharacterStyleRange>
        <CharacterStyleRange AppliedCharacterStyle="..." FontStyle="Bold" Underline="true">
          <Content>id imperdiet et</Content>
        </CharacterStyleRange>
        ...
        </ParagraphStyleRange>
        ``
        :param dict element_dict: dict representation of html element
        :param bool tail: if element has tail
        :return:

        """

        characterstylerange_list = []

        def apply_tag_style(characterstylerange, tag):
            for rule in self.INLINE_TAGS_MAPPING[tag]:
                attribute = rule['attribute']
                value = rule['value']
                appendable = rule['appendable']

                if characterstylerange.get(attribute) and appendable:
                    if attribute == 'FontStyle' and value == 'Bold':
                        characterstylerange.set(
                            attribute,
                            '{} {}'.format(value, characterstylerange.get(attribute))
                        )
                    else:
                        characterstylerange.set(
                            attribute,
                            '{} {}'.format(characterstylerange.get(attribute), value)
                        )
                else:
                    characterstylerange.set(attribute, value)

        # text
        if element_dict['text'] and len(element_dict['text']):
            characterstylerange_list.append(
                etree.Element('CharacterStyleRange', attrib=self.CHARACTERSTYLERANGE_DEFAULTS)
            )
            # apply parents styles
            for tag in element_dict['parents']:
                if self.INLINE_TAGS_MAPPING.get(tag):
                    apply_tag_style(characterstylerange_list[-1], tag)

            # apply own style
            tag = element_dict['tag']
            if self.INLINE_TAGS_MAPPING.get(tag):
                apply_tag_style(characterstylerange_list[-1], tag)

            content = etree.Element('Content')
            content.text = element_dict['text']

            if tag == 'a':
                self.links.append({
                    'self_id': '{}_{}'.format(self.self_id, len(self.links) + 1),
                    'text': element_dict['text'],
                    'href': element_dict['attrib'].get('href')
                })

                hyperlinktextsource = etree.SubElement(
                    characterstylerange_list[-1],
                    'HyperlinkTextSource',
                    attrib=self.merge_attributes(
                        self.HYPERLINKTEXTSOURCE_DEFAULTS,
                        {
                            'Self': self.links[-1]['self_id'],
                            'Name': 'Hyperlink {}'.format(self.links[-1]['self_id']),
                        }
                    )
                )
                hyperlinktextsource.append(content)
            else:
                characterstylerange_list[-1].append(content)

        # childs
        for child in element_dict['childs']:
            characterstylerange_list += self._create_characterstylerange_recursive(child, tail=True)

        # tail
        if tail and element_dict['tail'] and len(element_dict['tail']):
            characterstylerange_list.append(
                etree.Element(
                    'CharacterStyleRange',
                    attrib=self.CHARACTERSTYLERANGE_DEFAULTS
                )
            )
            # apply parents styles
            for tag in element_dict['parents']:
                if self.INLINE_TAGS_MAPPING.get(tag):
                    apply_tag_style(characterstylerange_list[-1], tag)

            content = etree.SubElement(
                characterstylerange_list[-1],
                'Content'
            )
            content.text = element_dict['tail']

        return characterstylerange_list

    @property
    def length(self):
        return len(" ".join(etree.XPath(".//text()")(self._element)))

    @staticmethod
    def guess_height(story, inner_width):
        style = story._etree.xpath('.//ParagraphStyleRange')[-1].get('AppliedParagraphStyle')
        if not style:
            return 100

        style = style.rsplit('%3a', 1)[-1]
        style_map = {
            'Headline': {
                'PointSize': 48,
                'Leading': 48,
                'LeftIndent': 0,
                'RightIndent': 0
            },
            'Byline': {
                'PointSize': 20,
                'Leading': 20,
                'LeftIndent': 0,
                'RightIndent': 0
            },
            'Heading1': {
                'PointSize': 40,
                'Leading': 40,
                'LeftIndent': 0,
                'RightIndent': 0
            },
            'Heading2': {
                'PointSize': 30,
                'Leading': 30,
                'LeftIndent': 0,
                'RightIndent': 0
            },
            'Heading3': {
                'PointSize': 20,
                'Leading': 20,
                'LeftIndent': 0,
                'RightIndent': 0
            },
            'Heading4': {
                'PointSize': 14,
                'Leading': 14,
                'LeftIndent': 0,
                'RightIndent': 0
            },
            'Heading5': {
                'PointSize': 11,
                'Leading': 11,
                'LeftIndent': 0,
                'RightIndent': 0
            },
            'Heading6': {
                'PointSize': 9,
                'Leading': 9,
                'LeftIndent': 0,
                'RightIndent': 0
            },
            'Blockquote': {
                'PointSize': 12,
                'Leading': 12,
                'LeftIndent': 30,
                'RightIndent': 30
            },
            'default': {
                'PointSize': 12,
                'Leading': 12,
                'LeftIndent': 0,
                'RightIndent': 0
            }
        }

        point_size = style_map.get(style, style_map['default'])['PointSize']
        leading = style_map.get(style, style_map['default'])['Leading']
        left_indent = style_map.get(style, style_map['default'])['LeftIndent']
        right_indent = style_map.get(style, style_map['default'])['RightIndent']

        length = story.length
        inner_width -= float(left_indent) + float(right_indent)
        length *= float(point_size) / style_map['default']['PointSize']
        length *= float(leading) / style_map['default']['Leading']
        height = length / inner_width * 75 + 10

        return height
