from lxml import etree

from .base import BasePackageElement


class Designmap(BasePackageElement):
    """
    As Adobe's idml specification explains:
    ``Thee designmap.xml file is the key to all of the other files that appear within the IDML package.
    This file specifies the order in which the spreads appear in the document,
    maintains the cross references between the resources and content of the file,
    and defines a variety of document-level attributes not supported by other files.``
    """

    AID_DECLARATION = '<?aid style="50" type="document" readerVersion="6.0" featureSet="257"?>'
    HYPERLINK_DEFAULTS = {
        'Visible': 'false',
        'Highlight': 'None',
        'Width': 'Thin',
        'BorderStyle': 'Solid',
        'Hidden': 'false',
    }

    def __init__(self, attributes=None):
        super().__init__(attributes)
        self._links_counter = 0

    @property
    def filename(self):
        """
        Filename inside IDML package.
        Used as a filename for a file inside zip container.
        :return str: filename
        """
        return 'designmap.xml'

    def _build_etree(self):
        self._etree = etree.Element(
            'Document',
            nsmap={'idPkg': self.XMLNS_IDPKG}
        )
        self._etree.set('DOMVersion', self.DOM_VERSION)

    def render(self):
        """
        Render object to xml.
        Used as a content for a file inside a zip container.
        :return str: content of the file inside zip/idml container.
        """
        return self.XML_DECLARATION + '\n' + \
            self.AID_DECLARATION + '\n' + \
            etree.tostring(self._etree, pretty_print=True).decode('utf-8')

    def add_pkg(self, tag, src):
        """
        Add a package which will be specified in the designmap.xml
        :param str tag: xml tag name
        :param str src: relative source path (inside idml) to the linked package.
        :return:
        """
        return etree.SubElement(
            self._etree,
            etree.QName(self.XMLNS_IDPKG, tag),
            attrib={'src': src},
            nsmap={'idPkg': self.XMLNS_IDPKG},
        )

    def add_hyperlinks(self, links):
        """
        Add links to hyperlinks inside designmap.xml.
        :param list links: list of dicts.
        """
        for link in links:
            self._links_counter += 1
            hyperlinkurldestination = etree.SubElement(
                self._etree,
                'HyperlinkURLDestination',
                {
                    'Self': 'HyperlinkURLDestination/{}'.format(link['href']),
                    'Name': link['href'],
                    'DestinationURL': link['href'],
                    'Hidden': 'false',
                    'DestinationUniqueKey': str(self._links_counter),
                }
            )
            hyperlink = etree.SubElement(
                self._etree,
                'Hyperlink',
                self.merge_attributes(
                    self.HYPERLINK_DEFAULTS,
                    {
                        'Self': 'u{}'.format(self._links_counter),
                        'Name': link['text'],
                        'Source': link['self_id'],
                        'DestinationUniqueKey': str(self._links_counter),
                    }
                )
            )
            properties = etree.SubElement(hyperlink, 'Properties')
            bordercolor = etree.SubElement(properties, 'BorderColor', attrib={'type': 'enumeration'})
            bordercolor.text = 'Black'
            etree.SubElement(properties, 'Destination', attrib={'type': 'object'})
            bordercolor.text = hyperlinkurldestination.get('DestinationUniqueKey')
