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
        :type stream: `io.BytesIO` | `io.BufferedReader` | `io.BufferedIOBase` | `werkzeug.datastructures.FileStorage`
        :param filename: filename
        :type filename: str
        """

        content_type = None

        try:
            stream = content
            if type(content) is datastructures.FileStorage:
                stream = content.stream
            stream_type = type(stream)
            try:
                # we expect types with `io.BufferedIOBase` interface
                bytes_buffer = stream.read()
                stream.seek(0)
            except AttributeError:
                msg = 'Not expected format for incoming binary stream: {}'.format(stream_type)
                logger.warning(msg)
                raise Exception(msg)
            # detect mimetype using wrapper around libmagic
            content_type = magic.Magic(mime=True).from_buffer(bytes_buffer)

            # if 'application/octet-stream' is returned it means that libmagic was not able to
            # detect mimetype precisely and as a fallback 'application/octet-stream' was returned.
            # in this case we should try to detect a mimetype by filename
            if content_type == 'application/octet-stream':
                msg = 'libmagic was not able to detect mimetype precisely'
                raise Exception(msg)
        except Exception as e:
            logger.warning(e)
            if filename:
                # detect mimetype using filename extension
                guessed_content_type = mimetypes.MimeTypes().guess_type(filename)[0]
                if guessed_content_type:
                    content_type = guessed_content_type

        return content_type
