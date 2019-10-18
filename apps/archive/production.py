
from superdesk.resource import build_custom_hateoas
from .archive import ArchiveResource, ArchiveService
from .common import CUSTOM_HATEOAS


class ProductionResource(ArchiveResource):
    datasource = ArchiveResource.datasource.copy()
    datasource.update({
        'source': 'archive',
        'elastic_filter': {'bool': {
            'must_not': {'term': {'version': 0}}
        }},
    })

    resource_methods = ['GET']
    item_methods = []


class ProductionService(ArchiveService):

    def get(self, req, lookup):
        docs = super().get(req, lookup)
        for doc in docs:
            build_custom_hateoas(CUSTOM_HATEOAS, doc)
        return docs
