from lxml import etree


from .base import BasePackageElement


class Tags(BasePackageElement):
    """
    As Adobe's idml specification explains:
     ``
     The Tags.xml file contains the XML tag de nitions stored in the InDesign document,
     including unused tags.
     ``
    """

    DEFAULT_TAGS = {
        'Root': {
            'TagColor': 'LightBlue'
        }
    }

    @property
    def filename(self):
        """
        Filename inside IDML package.
        Used as a filename for a file inside zip container.
        :return str: filename
        """
        return 'XML/Tags.xml'

    def _build_etree(self):
        self._etree = etree.Element(
            etree.QName(self.XMLNS_IDPKG, 'Tags'),
            nsmap={'idPkg': self.XMLNS_IDPKG}
        )
        self._etree.set('DOMVersion', self.DOM_VERSION)
        self._add_xmltags()

    def _add_xmltags(self):
        """
        Add XMLTag(s)
        """
        tags = self.merge_attributes(self.DEFAULT_TAGS, self._attributes)

        for tag in tags:
            # XMLTag
            xmltag = etree.SubElement(
                self._etree,
                'XMLTag',
                attrib={
                    'Self': 'XMLTag/{}'.format(tag),
                    'Name': tag,
                }
            )
            # Properties
            properties = etree.SubElement(
                xmltag,
                'Properties'
            )
            # TagColor
            tagcolor = etree.SubElement(
                properties,
                'TagColor',
                attrib={
                    'type': 'enumeration'
                }
            )
            tagcolor.text = tags[tag]['TagColor']
