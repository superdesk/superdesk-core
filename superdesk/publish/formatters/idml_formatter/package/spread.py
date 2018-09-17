from lxml import etree

from superdesk.utils import merge_dicts_deep

from .base import BasePackageElement


class Spread(BasePackageElement):
    """
    As Adobe's idml specification explains:
      ``
       The Spreads folder contains the XML files representing the spreads in the document.
       Each spread contains all of the page items (rectangles, ellipses, graphic lines, polygons, groups, buttons,
       and text frames) that appear on the pages of the spread.
       The <Spread> element also contains <Page> elements, which contain attributes and elements that relate
       to the pages of the spread. Note that <Page> elements do not contain page items.
       Spreads do not contain text stream content — the <TextFrame> XML elements in the spread refer
       to <Story> elements contained the files in the Stories folder.
      ``
    """

    SPREAD_DEFAULTS = {
        'FlattenerOverride': 'Default',
        'ShowMasterItems': 'true',
        'PageCount': '1',
        'BindingLocation': '0',
        'AllowPageShuffle': 'true',
        'ItemTransform': '1 0 0 1 0 0',
        'PageTransitionType': 'None',
        'PageTransitionDirection': 'NotApplicable',
        'PageTransitionDuration': 'Medium'
    }
    PAGE_DEFAULTS = {
        'AppliedTrapPreset': 'TrapPreset/$ID/kDefaultTrapStyleName',
        'AppliedMaster': 'n',
        'OverrideList': '',
        'TabOrder': '',
        'GridStartingPoint': 'TopOutside',
        'UseMasterGrid': 'true'
    }
    MARGINPREFERENCE_DEFAULTS = {
        'ColumnCount': '1',
        'ColumnGutter': '12',
        'Top': '36',
        'Bottom': '36',
        'Left': '36',
        'Right': '36',
        'ColumnDirection': 'Horizontal',
        'ColumnsPositions': '0 540'
    }
    TEXTFRAME_DEFAULTS = {
        'ItemTransform': "1 0 0 1 0 0",
        'ContentType': "TextType"
    }
    GEOMETRYPATH_DEFAULTS = {
        'PathOpen': 'false'
    }
    VERTICAL_MARGIN = 10

    def __init__(self, self_id, document_page_width, document_page_height, attributes=None):
        self.self_id = self_id
        self._spread = None
        self._page = None
        self._document_page_width = document_page_width
        self._document_page_height = document_page_height
        super().__init__(attributes)

    @property
    def filename(self):
        """
        Filename inside IDML package.
        Used as a filename for a file inside zip container.
        :return str: filename
        """
        return 'Spreads/Spread_{}.xml'.format(self.self_id)

    @property
    def page_inner_height(self):
        return self._document_page_height - self._page_margins['top'] - self._page_margins['bottom']

    @staticmethod
    def _make_itemtransform_translation(matrix, coordiantes):
        """
        Translate matrix according to provided coordinates.
        :param tuple matrix: initial matrix
        :param tuple coordiantes: typle (x, y)
        :return:
        """
        # x
        matrix[2][0] += coordiantes[0]
        # y
        matrix[2][1] += coordiantes[1]

        return matrix

    @property
    def _initial_itemtransform_matrix(self):
        """
        :return tuple: initial matrix for item transform
        """
        margins = self._page_margins

        return (
            [1, 0],
            [0, 1],
            [
                self._document_page_width / 2 * (-1) + margins['right'],
                self._document_page_height / 2 * (-1) + margins['top']
            ]
        )

    @property
    def _last_used_pathpoints(self):
        """
        :return list: list of dicts with last used pathpoints
        """
        elements = self._spread.xpath('.//PathPointArray')

        if not elements:
            return None

        pathpointarray = elements[-1]

        return [
            {
                k: [
                    float(i) for i in el.attrib[k].split()
                ] for k in el.attrib
            } for el in pathpointarray
        ]

    @property
    def _last_used_itemtransform(self):
        """
        Return a last (lowest) TextFrame/Rectangle's ItemTransform as a matrix
        :return tuple: last used item transform as a matrix
        """
        elements = self._spread.xpath('*[self::TextFrame|self::Rectangle]')

        if not elements:
            return None

        _transform = [float(i) for i in elements[-1].get('ItemTransform').split()]

        return (
            _transform[:2],
            _transform[2:4],
            _transform[4:]
        )

    @property
    def _page_margins(self):
        """
        :return dict: page margins info
        """
        if self._page is None:
            # TODO create custom exception
            raise Exception('Page does not exist.')

        return {
            'top': float(self._page.find('MarginPreference').attrib['Top']),
            'bottom': float(self._page.find('MarginPreference').attrib['Bottom']),
            'left': float(self._page.find('MarginPreference').attrib['Left']),
            'right': float(self._page.find('MarginPreference').attrib['Right'])
        }

    def add_page(self, attributes=None):
        """
        Add page to the spread.
        :param dict attributes: custom page attributes
        :return lxml.etree: Page etree instance
        """
        # for now only 1 page per spread is supported
        if self._page is not None:
            return False

        # merge Page attributes
        page_attributes = self.PAGE_DEFAULTS
        if attributes:
            page_attributes = self.merge_attributes(
                page_attributes,
                attributes.get('Page', {})
            )
        # Page
        self._page = etree.SubElement(
            self._spread,
            'Page',
            attrib=page_attributes
        )
        # merge MarginPreference attributes
        marginpreference_attributes = self.MARGINPREFERENCE_DEFAULTS
        if attributes:
            marginpreference_attributes = self.merge_attributes(
                marginpreference_attributes,
                attributes.get('MarginPreference', {})
            )
        # MarginPreference
        etree.SubElement(
            self._page,
            'MarginPreference',
            attrib=marginpreference_attributes
        )

        return self._page

    def has_page(self):
        return self._page is not None

    def place_textframe(self, height, attributes=None):
        """
        Place textframe in the spread. Text frame has link to the story.
        :param int height: text frame height
        :param attributes: custom text frame attributes
        """
        if height < 20:
            height = 20

        modifier = {
            'TextFrame': {
                'ItemTransform': self._generate_next_itemtransform()
            }
        }

        if attributes:
            attributes = dict(merge_dicts_deep(attributes, modifier))
        else:
            attributes = modifier

        textframe = self._create_textframe(attributes)

        # Properties
        properties = etree.SubElement(
            textframe,
            'Properties'
        )
        pathgeometry = self._create_pathgeometry(height)
        properties.append(pathgeometry)

    def check_if_fits(self, height):
        """
        Check if text frame with provided `height` will fit in page.
        :param int height: height to check
        :return bool: True or False
        """
        # 0:0 is at the center of the page when facing pages is off
        highest_possible_y_axis_point = self.page_inner_height / 2
        required_y_axis_point = float(
            self._generate_next_itemtransform().rsplit(maxsplit=1)[-1]
        ) + height + self.VERTICAL_MARGIN

        return highest_possible_y_axis_point >= required_y_axis_point

    def _build_etree(self):
        self._etree = etree.Element(
            etree.QName(self.XMLNS_IDPKG, 'Spread'),
            nsmap={'idPkg': self.XMLNS_IDPKG}
        )
        self._etree.set('DOMVersion', self.DOM_VERSION)
        self._add_spread()

    def _add_spread(self):
        """
        Create <Spread..> tag
        :return lxml.etree: Spread etree instance
        """
        # merge Spread attributes
        spread_attributes = self.merge_attributes(
            self.SPREAD_DEFAULTS,
            self._attributes.get('Spread', {})
        )
        spread_attributes.update({'Self': self.self_id})
        # Spread
        self._spread = etree.SubElement(
            self._etree,
            'Spread',
            attrib=spread_attributes
        )

        return self._spread

    def _create_textframe(self, attributes=None):
        """
        Create <TextFrame..> tag
        :param dict attributes: custom attributes
        :return lxml.etree: TextFrame lxml instance
        """

        # merge TextFrame attributes
        textframe_attributes = self.TEXTFRAME_DEFAULTS
        if attributes:
            textframe_attributes = self.merge_attributes(
                textframe_attributes,
                attributes.get('TextFrame', {})
            )
        # Page
        textframe = etree.SubElement(
            self._spread,
            'TextFrame',
            attrib=textframe_attributes
        )

        return textframe

    def _create_pathgeometry(self, height):
        """
        Create <PathGeometry..> tag
        :param int height: height
        :return lxml.etree: PathGeometry lxml instance
        """
        # for rectangle frames only

        # PathGeometry
        pathgeometry = etree.Element(
            'PathGeometry'
        )
        # GeometryPath
        geometrypath = etree.SubElement(
            pathgeometry,
            'GeometryPath',
            attrib=self.GEOMETRYPATH_DEFAULTS
        )
        # PathPointArray
        pathpointarray = etree.SubElement(
            geometrypath,
            'PathPointArray'
        )
        # PathPoint(s)
        margins = self._page_margins
        internal_page_width = self._document_page_width - margins['right'] - margins['left']
        pathpoints_coordinates = [
            # left top
            [0, 0],
            # left bottom
            [0, height],
            # right bottom
            [internal_page_width, height],
            # right top
            [internal_page_width, 0],
        ]

        for coordiantes in pathpoints_coordinates:
            etree.SubElement(
                pathpointarray,
                'PathPoint',
                attrib={
                    'Anchor': '{} {}'.format(*coordiantes),
                    'LeftDirection': '{} {}'.format(*coordiantes),
                    'RightDirection': '{} {}'.format(*coordiantes),
                }
            )

        return pathgeometry

    def _generate_next_itemtransform(self):
        """
        :return str: item transform for the next text frame element
        """
        matrix = self._last_used_itemtransform

        if matrix:
            matrix = self._make_itemtransform_translation(matrix, (0, self.VERTICAL_MARGIN))
            # add frame height
            matrix = self._make_itemtransform_translation(matrix, (0, self._last_used_pathpoints[1]['Anchor'][1]))
        else:
            matrix = self._initial_itemtransform_matrix

        return '{:.0f} {:.0f} {:.0f} {:.0f} {} {}'.format(
            matrix[0][0], matrix[0][1],
            matrix[1][0], matrix[1][1],
            matrix[2][0], matrix[2][1],
        )
