"""
News resource
=============

It is an alias for archive without filtering out published items.
"""


from superdesk.resource import build_custom_hateoas
from .common import CUSTOM_HATEOAS
from .resource import ArchiveResource
from .archive import ArchiveService


class NewsResource(ArchiveResource):
    datasource = ArchiveResource.datasource.copy()
    datasource.update(
        {
            "source": "archive",
            "elastic_filter": {"bool": {"must_not": {"term": {"version": 0}}}},
        }
    )

    resource_methods = ["GET"]
    item_methods = []


class NewsService(ArchiveService):
    def enhance_items(self, items):
        super().enhance_items(items)
        for item in items:
            build_custom_hateoas(CUSTOM_HATEOAS, item)
