from .base import BasePackageElement


class Mimetype(BasePackageElement):
    MIMETYPE = 'application/vnd.adobe.indesign-idml-package'

    @property
    def filename(self):
        """
        Filename inside IDML package.
        Used as a filename for a file inside zip container.
        :return str: filename
        """
        return 'mimetype'

    def _build_etree(self):
        pass

    def render(self):
        return self.MIMETYPE
