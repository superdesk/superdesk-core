from ..service import ProdApiService


class ContactsService(ProdApiService):
    excluded_fields = {
        '_etag',
        '_type',
        '_updated',
        '_created',
        '_links'
    }
