from lxml import etree


from .base import BasePackageElement


class Preferences(BasePackageElement):
    """
    As Adobe's idml specification explains:
       ``
       The Preferences.xml file contains representations of all of the document preferences.
       ``
    """

    DOCUMENTPREFERENCE_DEFAULTS = {
        "PageHeight": "792",
        "PageWidth": "612",
        "PagesPerDocument": "1",
        "FacingPages": "true",
        "DocumentBleedTopOffset": "0",
        "DocumentBleedBottomOffset": "0",
        "DocumentBleedInsideOrLeftOffset": "0",
        "DocumentBleedOutsideOrRightOffset": "0",
        "DocumentBleedUniformSize": "true",
        "SlugTopOffset": "0",
        "SlugBottomOffset": "0",
        "SlugInsideOrLeftOffset": "0",
        "SlugRightOrOutsideOffset": "0",
        "DocumentSlugUniformSize": "false",
        "PreserveLayoutWhenShuffling": "true",
        "AllowPageShuffle": "true",
        "OverprintBlack": "true",
        "PageBinding": "LeftToRight",
        "ColumnDirection": "Horizontal",
        "Intent": "PrintIntent",
    }

    @property
    def filename(self):
        """
        Filename inside IDML package.
        Used as a filename for a file inside zip container.
        :return str: filename
        """
        return "Resources/Preferences.xml"

    def _build_etree(self):
        self._etree = etree.Element(etree.QName(self.XMLNS_IDPKG, "Preferences"), nsmap={"idPkg": self.XMLNS_IDPKG})
        self._etree.set("DOMVersion", self.DOM_VERSION)
        self._add_documentpreference()

    def _add_documentpreference(self):
        """
        Add <DocumentPreference..> and fill it with properties.
        :return lxml.etree: DocumentPreference
        """
        # DocumentPreference
        documentpreference = etree.SubElement(
            self._etree,
            "DocumentPreference",
            attrib=self.merge_attributes(
                self.DOCUMENTPREFERENCE_DEFAULTS, self._attributes.get("DocumentPreference", {})
            ),
        )
        # Properties
        properties = etree.SubElement(documentpreference, "Properties")
        # ColumnGuideColor
        columnguidecolor = etree.SubElement(properties, "ColumnGuideColor")
        columnguidecolor.set("type", "enumeration")
        columnguidecolor.text = "Violet"
        # MarginGuideColor
        marginguidecolor = etree.SubElement(properties, "MarginGuideColor")
        marginguidecolor.set("type", "enumeration")
        marginguidecolor.text = "Magenta"

        return documentpreference
