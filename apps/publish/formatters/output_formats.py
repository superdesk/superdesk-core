import superdesk

from superdesk.utils import ListCursor
from superdesk.publish.formatters import get_all_formatters


class OutputFormatsResource(superdesk.Resource):
    item_methods = []
    resource_methods = ["GET"]
    schema = {
        "type": {"type": "string"},
        "name": {"type": "string"},
    }


class OutputFormatsService(superdesk.Service):
    def get(self, req, lookup):
        """Return list of available output formats."""

        values = [
            dict(name=formatter.name, type=formatter.type)
            for formatter in get_all_formatters()
            if getattr(formatter, "name", None) is not None
        ]

        codes = set()
        unique_values = []
        for value in values:
            if value["type"] in codes:
                continue
            codes.add(value["type"])
            unique_values.append(value)

        unique_values.sort(key=lambda x: x["name"].lower())
        return ListCursor(unique_values)
