import io
import logging

from .utils import get_mimetype


logger = logging.getLogger(__name__)


class MimetypeMixin:
    def _get_mimetype(self, content, filename=None, content_type=None):
        """
        Return mimetype of the `content` and as a fallback using `filename`

        :param content: binary stream
        :type stream: `io.BytesIO` | `io.BufferedReader` | `io.BufferedIOBase` | `werkzeug.datastructures.FileStorage`
        :param filename: filename
        :type filename: str
        :param content_type: expected content type, used as a fallback
        :type filename: str
        """

        return get_mimetype(content, filename, content_type)
