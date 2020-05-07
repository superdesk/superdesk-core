# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.metadata.item import metadata_schema
from superdesk.metadata.utils import extra_response_fields, item_url, aggregations, get_elastic_highlight_query
from eve.methods.common import resolve_document_etag
from superdesk import get_resource_service
from eve.utils import config
from flask import current_app as app
from apps.auth import get_user
from superdesk.notification import push_notification
import superdesk

SOURCE = 'ingest'


class IngestResource(Resource):
    schema = {
        'archived': {
            'type': 'datetime'
        }
    }
    schema.update(metadata_schema)
    extra_response_fields = extra_response_fields
    item_url = item_url
    datasource = {
        'search_backend': 'elastic',
        'aggregations': aggregations,
        'es_highlight': get_elastic_highlight_query
    }
    privileges = {'DELETE': 'fetch'}


class IngestService(BaseService):

    def post_in_mongo(self, docs, **kwargs):
        for doc in docs:
            self._resolve_defaults(doc)
        self.on_create(docs)
        resolve_document_etag(docs, self.datasource)
        ids = self.backend.create_in_mongo(self.datasource, docs, **kwargs)
        self.on_created(docs)
        return ids

    def patch_in_mongo(self, id, document, original):
        res = self.backend.update_in_mongo(self.datasource, id, document, original)
        return res

    def set_ingest_provider_sequence(self, item, provider):
        """Sets the value of ingest_provider_sequence in item.

        :param item: object to which ingest_provider_sequence to be set
        :param provider: ingest_provider object, used to build the key name of sequence
        """
        sequence_number = get_resource_service('sequences').get_next_sequence_number(
            key_name='ingest_providers_{_id}'.format(_id=provider[config.ID_FIELD]),
            max_seq_number=app.config['MAX_VALUE_OF_INGEST_SEQUENCE']
        )
        item['ingest_provider_sequence'] = str(sequence_number)

    def on_deleted(self, docs):
        docs = docs if isinstance(docs, list) else [docs]
        file_ids = [rend.get('media')
                    for doc in docs
                    for rend in doc.get('renditions', {}).values()
                    if not doc.get('archived') and rend.get('media')]

        for file_id in file_ids:
            superdesk.app.media.delete(file_id)

        ids = [ref.get('residRef')
               for doc in docs
               for group in doc.get('groups', {})
               for ref in group.get('refs', {})
               if ref.get('residRef')]

        if ids:
            self.delete({'_id': {'$in': ids}})

        user = get_user(required=True)
        if docs:
            push_notification('item:deleted', item=str(docs[0].get(config.ID_FIELD)), user=str(user))
