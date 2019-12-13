# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import logging
import superdesk

from flask import json
from flask_babel import _
from eve.utils import config

from superdesk import get_resource_service
from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError, ProviderError
from superdesk.resource import Resource
from apps.archive.common import ARCHIVE, insert_into_versions, fetch_item

logger = logging.getLogger(__name__)


class ProviderNotFoundError(SuperdeskApiError):
    pass


class SearchIngestResource(superdesk.Resource):
    resource_methods = ['GET', 'POST']
    schema = {
        'guid': {'type': 'string', 'required': True},
        'desk': Resource.rel('desks', False, nullable=True),
        'stage': Resource.rel('stages', False, nullable=True)
    }


class SearchIngestService(superdesk.Service):
    def __init__(self, datasource=None, backend=None, source=None):
        super().__init__(datasource, backend)
        self.source = source

    def get_provider(self):
        provider = get_resource_service('search_providers').find_one(source=self.source, req=None)
        if provider and 'config' in provider and 'username' in provider['config']:
            self.backend.set_credentials(provider['config']['username'], provider['config'].get('password', ''))
        return provider

    def fetch(self, guid):
        return self.backend.find_one_raw(guid, guid)

    def create(self, docs, **kwargs):
        new_guids = []
        provider = self.get_provider()
        for doc in docs:
            if not doc.get('desk'):
                # if no desk is selected then it is bad request
                raise SuperdeskApiError.badRequestError(_("Destination desk cannot be empty."))
            try:
                archived_doc = self.fetch(doc['guid'])
            except FileNotFoundError as ex:
                raise ProviderError.externalProviderError(ex, provider)

            dest_doc = fetch_item(archived_doc, doc.get('desk'), doc.get('stage'), state=doc.get('state'))
            new_guids.append(dest_doc['guid'])

            if provider:
                dest_doc['ingest_provider'] = str(provider[superdesk.config.ID_FIELD])

            superdesk.get_resource_service(ARCHIVE).post([dest_doc])
            insert_into_versions(dest_doc.get('_id'))

        if new_guids:
            get_resource_service('search_providers').system_update(provider.get(config.ID_FIELD),
                                                                   {'last_item_update': utcnow()}, provider)

        return new_guids

    def get(self, req, lookup):
        provider = self.get_provider()
        if provider:
            query = self._get_query(req)
            results = self.backend.find(self.source, query, None)
            for doc in results.docs:
                doc['ingest_provider'] = str(provider[superdesk.config.ID_FIELD])
            return results
        else:
            raise ProviderNotFoundError(_('provider not found source={source}').format(source=self.source))

    def fetch_rendition(self, rendition):
        """Get file stream for given rendition specs.

        Rendition should be from item that was fetched via this service get method.
        It can use api authentication if needed to fetch this binary.

        :param rendition: rendition dict
        """
        self.get_provider()
        return self.backend.fetch_file(rendition.get('href'))

    def _get_query(self, req):
        args = getattr(req, 'args', {})
        query = json.loads(args.get('source')) if args.get('source') else {'query': {'filtered': {}}}
        return query
