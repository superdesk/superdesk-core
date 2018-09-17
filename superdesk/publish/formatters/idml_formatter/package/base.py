from abc import ABC, abstractmethod
from lxml import etree

from superdesk.utils import merge_dicts_deep


class BasePackageElement(ABC):
    """
    Represent a single file inside an idml package.
    Each class who inherits this class must implement next methods:
     - `self.filename`
     - `self._build_etree`
    """

    XML_DECLARATION = '<?xml version="1.0" encoding="utf-8"?>'
    XMLNS_IDPKG = 'http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging'
    DOM_VERSION = '13.1'

    def __init__(self, attributes=None):
        super().__init__()
        self._etree = None
        self._attributes = {}

        if attributes:
            self._attributes = attributes

        self._build_etree()

    @property
    @abstractmethod
    def filename(self):
        """
        Filename inside IDML package.
        Used as a filename for a file inside zip container.
        Method must be implemented by inheritor class.
        """
        pass

    @abstractmethod
    def _build_etree(self):
        """
        Use `self._etree` for lxml.etree content representation.
        :return:
        """
        pass

    def render(self):
        """
        Render object to xml/text.
        Used as a content for a file inside a zip container.
        :return str: content of the file inside zip/idml container.
        """
        return self.XML_DECLARATION + '\n' + etree.tostring(self._etree, pretty_print=True).decode('utf-8')

    @staticmethod
    def merge_attributes(attributes1, attributes2):
        """
        Deep merge of 2 dicts.
        :param dict attributes1: 1st dict
        :param dict attributes2: 2nd dict
        :return dict: merged dict
        """
        return dict(merge_dicts_deep(attributes1, attributes2))
