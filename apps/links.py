
import superdesk

from flask import request, current_app as app
from superdesk.resource import build_custom_hateoas

from apps.archive.archive import ArchiveResource, ArchiveService
from apps.archive.common import CUSTOM_HATEOAS


def elastic_filter():
    guid = request.args.get('guid')
    uri = request.args.get('uri') or guid
    assert guid

    query = {
        'bool': {
            'should': [
                {'term': {'refs.uri': uri}},
                {'term': {'refs._id': guid}},
                {'term': {'refs.guid': guid}},
            ],
        },
    }

    LINKS_DAYS = app.config.get('LINKS_MAX_DAYS')
    if LINKS_DAYS:
        query['bool'].update({
            'minimum_should_match': 1,
            'must': {
                'range': {
                    'versioncreated': {
                        'gte': 'now-{}d/d'.format(int(LINKS_DAYS)),
                    },
                },
            },
        })

    return query


class LinksResource(ArchiveResource):
    item_methods = []
    resource_methods = ['GET']
    datasource = ArchiveResource.datasource.copy()
    datasource.update({
        'source': 'archive',
        'elastic_filter_callback': elastic_filter,
        'elastic_filter': {'bool': {
            'must_not': {'term': {'version': 0}}
        }},
    })


class LinksService(ArchiveService):
    def enhance_items(self, items):
        super().enhance_items(items)
        for item in items:
            build_custom_hateoas(CUSTOM_HATEOAS, item)


def init_app(_app):
    superdesk.register_resource('links', LinksResource, _app=_app)
