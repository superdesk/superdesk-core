import io
import logging
import mimetypes

import magic
from werkzeug import datastructures


logger = logging.getLogger(__name__)


class MimetypeMixin:

    def _get_mimetype(self, content, filename=None):
        """
        Return mimetype of the `content` and as a fallback using `filename`

        :param content: binary stream
        :type stream: `io.BufferedIOBase` | `io.BytesIO` | `werkzeug.datastructures.FileStorage`
        :param filename: filename
        :type filename: str
        """

        content_type = None

        try:
            stream = content
            if type(content) is datastructures.FileStorage:
                stream = content.stream
            stream_type = type(stream)
            if stream_type is io.BufferedIOBase:
                bytes_buffer = stream.read(size=None)
            elif stream_type is io.BytesIO:
                bytes_buffer = stream.getvalue()
            else:
                msg = 'Not expected format for incoming binary stream: {}'.format(stream_type)
                logger.warning(msg)
                raise Exception(msg)
            content_type = magic.Magic(mime=True).from_buffer(bytes_buffer)
        except Exception:
            if filename:
                guessed_content_type = mimetypes.MimeTypes().guess_type(filename)[0]
                if guessed_content_type:
                    content_type = guessed_content_type

        return content_type
