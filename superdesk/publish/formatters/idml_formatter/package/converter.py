import io
import zipfile
from lxml import etree

from . import (
    Mimetype,
    Preferences,
    Styles,
    Tags,
    Story,
    StoryTable,
    StoryList,
    Spread,
    Designmap,
    Graphic
)


class Converter:
    """
    IDML Converter.

    Format items to `IDML <https://fileinfo.com/extension/idml>`
    """

    ZIP_COMPRESSION = zipfile.ZIP_STORED
    PAGE_MARGIN_TOP = 50
    PAGE_MARGIN_BOTTOM = 50
    PAGE_MARGIN_LEFT = 50
    PAGE_MARGIN_RIGHT = 50
    DOCUMENT_PAGE_HEIGHT = 841.8897637776
    DOCUMENT_PAGE_WIDTH = 595.2755905488
    DOCUMENT_PAGE_INNER_WIDTH = DOCUMENT_PAGE_WIDTH - PAGE_MARGIN_LEFT - PAGE_MARGIN_RIGHT

    def __init__(self):
        self._idml_bytes_buffer = None
        self._in_memory_zip = None
        self._package = []
        self._counter = {}

    def create_idml(self, article):
        """
        Creates idml file as in-memory zip container.

        IDML file is a zip container and it inludes the next files and folders:
         - mimetype
         - designmap.xml:
            Is the key to all of the other filles that appear within the IDML package.
         - XML:
            Folder contains XML elements and settings used in the InDesign document.
         - XML/Tags.xml:
            Contains the XML tag defnitions stored in the InDesign document.
         - Resources:
            Folder contains elements that are commonly used by other filles within the document,
            such as colors, fonts, and paragraph styles.
         - Resources/Graphic.xml:
            Contains the inks, colors, swatches, gradients, mixed inks, mixed ink groups, tints,
            and stroke styles contained in the document.
         - Resources/Preferences.xml:
            Contains representations of all of the document preferences.
         - Resources/Styles.xml:
            Contains all of the paragraph, character, object, cell, table, and TOC styles used in the document.
         - Spreads:
            Folder contains the XML  les representing the spreads in the document.
         - Spreads/Spread_spread_*.xml:
            Each spread contains all of the page items (rectangles, ellipses, graphic lines, polygons, groups,
            buttons, and text frames) that appear on the pages of the spread.
         - Stories:
            Folder contains all of the stories in the InDesign document.
         - Stories/Story_story_*.xml:
            Represents the contents of a single story and all of the formatting attributes applied to the
            text in the story.

        :param dict article: article data
        :return bytes: idml file as a bytes
        """
        self._counter = {'spread': 0, 'page': 0, 'story': 0, 'textframe': 0}
        self._init_zip_container()
        self._package = []
        self._package.append(Mimetype())
        self._package.append(Styles())
        self._package.append(Graphic())
        self._package.append(
            Preferences(attributes={
                'DocumentPreference': {
                    'PageHeight': str(self.DOCUMENT_PAGE_HEIGHT),
                    'PageWidth': str(self.DOCUMENT_PAGE_WIDTH),
                    'PagesPerDocument': '1',
                    'FacingPages': 'false'}
            })
        )
        self._package.append(
            Tags(attributes={
                'Headline': {'TagColor': 'Orange'},
                'Byline': {'TagColor': 'Orange'},
                'Heading1': {'TagColor': 'Red'},
                'Heading2': {'TagColor': 'Red'},
                'Heading3': {'TagColor': 'Red'},
                'Heading4': {'TagColor': 'Red'},
                'Heading5': {'TagColor': 'Red'},
                'Heading6': {'TagColor': 'Red'},
                'NormalParagraph': {'TagColor': 'Green'},
                'Blockquote': {'TagColor': 'Blue'},
                'Preformatted': {'TagColor': 'Black'},
                'Table': {'TagColor': 'Yellow'},
                'UnorderedList': {'TagColor': 'Pink'},
                'OrderedList': {'TagColor': 'Pink'}
            })
        )
        self._create_stories(article)
        self._create_spreads()
        self._create_designmap()
        self._write_package()
        self._in_memory_zip.close()

        return self._idml_bytes_buffer.getvalue()

    def _init_zip_container(self):
        """
        Creates zipfile with `x` (exclusively create and write a new file) mode.
        BytesIO file-like object is used for zipfile file reference.
        """
        self._idml_bytes_buffer = io.BytesIO()
        self._in_memory_zip = zipfile.ZipFile(
            self._idml_bytes_buffer,
            mode='x',
            compression=self.ZIP_COMPRESSION
        )

    def _write_package(self):
        """
        Write files into zip container.

        ``self._package`` includes only objects based on
        ``<class 'superdesk.publish.formatters.idml_formatter.package.base.BasePackageElement'>``,
        they know how to render itself (file content) and how to name itself.
        """
        for item in self._package:
            self._in_memory_zip.writestr(
                item.filename,
                item.render()
            )

    def _create_stories(self, article):
        """
        Walk thrrough `article['body_html']` and creates a Story/StoryTable/StoryList instances for each element.
        :param dict article: article data
        """

        body_html = article['body_html']

        if article.get('byline'):
            byline = etree.Element('byline')
            byline.text = article.get('byline')
            body_html = etree.tostring(byline, pretty_print=False).decode('utf-8') + body_html
        if article.get('headline'):
            headline = etree.Element('headline')
            headline.text = article.get('headline')
            body_html = etree.tostring(headline, pretty_print=False).decode('utf-8') + body_html

        parser = etree.HTMLParser(recover=True, remove_blank_text=True)
        root = etree.fromstring(body_html, parser)
        body = root.find('body')

        for element in body:
            if element.tag in ('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre', 'headline', 'byline'):
                # create text story
                self._package.append(
                    Story(
                        self._next_story_id(),
                        element,
                        attributes={
                            'ParagraphStyleRange': Story.BLOCK_TAGS_MAPPING[element.tag]['ParagraphStyleRange']
                        },
                        markup_tag=Story.BLOCK_TAGS_MAPPING[element.tag]['markup_tag']
                    )
                )
            elif element.tag in ('ul', 'ol'):
                # create list story
                self._package.append(
                    StoryList(
                        self._next_story_id(),
                        element,
                        attributes={
                            'ParagraphStyleRange': Story.BLOCK_TAGS_MAPPING[element.tag]['ParagraphStyleRange']
                        },
                        markup_tag=Story.BLOCK_TAGS_MAPPING[element.tag]['markup_tag']
                    )
                )
            elif element.tag == 'table':
                # create table story
                self._package.append(
                    StoryTable(
                        self._next_story_id(),
                        element,
                        self.DOCUMENT_PAGE_INNER_WIDTH,
                        attributes={
                            'Table': Story.BLOCK_TAGS_MAPPING[element.tag]['Table']
                        },
                        markup_tag=Story.BLOCK_TAGS_MAPPING[element.tag]['markup_tag']
                    )
                )

    def _create_spreads(self):
        """
        Walk through all stories, create a spread(s) and place stories into strpead(s).
        """
        active_spread = self._create_spread_with_page()

        # walk through packages and place them into spread->page
        for package in self._package:
            _type = type(package)
            if _type in (Story, StoryTable, StoryList):
                # guess height for a text frame (yes, table and lists are also textframes)
                text_frame_height = _type.guess_height(package, self.DOCUMENT_PAGE_INNER_WIDTH)

                # if guessed height for text frame is more than page height
                if text_frame_height > active_spread.page_inner_height:
                    text_frame_height = active_spread.page_inner_height

                # check if textframe will fit current page
                if not active_spread.check_if_fits(text_frame_height):
                    active_spread = self._create_spread_with_page()

                # place text frame
                active_spread.place_textframe(
                    height=text_frame_height,
                    attributes={
                        'TextFrame': {
                            'Self': self._next_textframe_id(),
                            'ParentStory': package.self_id,
                        }
                    }
                )

    def _create_designmap(self):
        """
        Create `Designmap` instance add it to the package.
        """
        designmap = Designmap()

        # let's fill designmap
        # order plays a big role
        for _type in (Graphic, Styles, Preferences, Tags, Spread, Story, StoryTable, StoryList):
            for obj in [i for i in self._package if i.__class__ is _type]:
                designmap.add_pkg(_type.__name__, obj.filename)

        for _type in (Story, StoryTable, StoryList):
            for obj in [i for i in self._package if i.__class__ is _type]:
                designmap.add_hyperlinks(obj.links)

        self._package.append(designmap)

    def _create_spread_with_page(self):
        """
        Create spread and put one page inside.
        :return Spread: spread instance
        """
        spread = Spread(
            self._next_spread_id(),
            document_page_width=self.DOCUMENT_PAGE_WIDTH,
            document_page_height=self.DOCUMENT_PAGE_HEIGHT,
        )
        self._package.append(spread)

        # create page
        page_id = self._next_page_id()
        spread.add_page(
            {
                'Page': {
                    'Self': page_id,
                    'Name': page_id,
                    'UseMasterGrid': 'false'
                },
                'MarginPreference': {
                    'Top': str(self.PAGE_MARGIN_TOP),
                    'Bottom': str(self.PAGE_MARGIN_BOTTOM),
                    'Left': str(self.PAGE_MARGIN_LEFT),
                    'Right': str(self.PAGE_MARGIN_RIGHT)
                },
            }
        )

        return spread

    def _next_story_id(self):
        """
        Generate a story id.
        :return str: story id
        """
        self_id = 'story_{}'.format(self._counter['story'])
        self._counter['story'] += 1
        return self_id

    def _next_spread_id(self):
        """
        Generate a spread id.
        :return str: spread id
        """
        self_id = 'spread_{}'.format(self._counter['spread'])
        self._counter['spread'] += 1
        return self_id

    def _next_page_id(self):
        """
        Generate a page id.
        :return str: page id
        """
        self_id = 'page_{}'.format(self._counter['page'])
        self._counter['page'] += 1
        return self_id

    def _next_textframe_id(self):
        """
        Generate a textframe id.
        :return str: textframe id
        """
        self_id = 'textframe_{}'.format(self._counter['textframe'])
        self._counter['textframe'] += 1
        return self_id
