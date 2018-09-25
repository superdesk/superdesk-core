import superdesk
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE
from superdesk.publish.formatters import Formatter
from superdesk.errors import FormatterError

from .package import Converter


class IDMLFormatter(Formatter):
    """
    IDML Formatter for Superdesk.

    Format items to `IDML <https://fileinfo.com/extension/idml>`
    """

    def __init__(self):
        # works with python 3.6
        # https://code.i-harness.com/en/q/c84c47
        # super().__init__()
        super(self.__class__, self).__init__()
        self.format_type = 'idml'

    def format(self, article, subscriber, codes=None):
        try:
            publish_seq_num = superdesk.get_resource_service('subscribers').generate_sequence_number(subscriber)
            idml_bytes = Converter().create_idml(article)
        except Exception as e:
            raise FormatterError.IDMLFormatterError(e, subscriber)

        return [
            {
                'published_seq_num': publish_seq_num,
                'encoded_item': idml_bytes,
                'formatted_item': '',
            }
        ]

    def export(self, article, subscriber, codes=None):
        """Formats the article and returns the output string for export"""
        raise NotImplementedError()

    def can_format(self, format_type, article):
        """
        Check if the article can be formatted to IDNL format.

        :param str format_type:
        :param dict article:
        :return bool: True if article can formatted else False
        """
        return format_type == self.format_type and article[ITEM_TYPE] in (CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED)
