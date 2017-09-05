# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from superdesk.logging import logger
from superdesk.utc import utcnow
from superdesk.notification import push_notification
from apps.content import push_expired_notification
from superdesk.errors import ProviderError
from superdesk.lock import lock, unlock
from superdesk.io.registry import registered_feeding_services


class RemoveExpiredContent(superdesk.Command):
    """Remove stale data from ingest based on the provider settings."""

    option_list = (
        superdesk.Option('--provider', '-p', dest='provider_name'),
    )

    def run(self, provider_name=None):
        providers = list(superdesk.get_resource_service('ingest_providers').get(req=None, lookup={}))
        self.remove_expired({'exclude': [str(p.get('_id')) for p in providers]})
        for provider in providers:
            if not provider_name or provider_name == provider.get('name'):
                self.remove_expired(provider)

    def remove_expired(self, provider):
        lock_name = 'ingest:gc'

        if not lock(lock_name, expire=300):
            return

        try:

            remove_expired_data(provider)
            push_notification('ingest:cleaned')
        except Exception as err:
            logger.exception(err)
            raise ProviderError.expiredContentError(err, provider)
        finally:
            unlock(lock_name)


superdesk.command('ingest:clean_expired', RemoveExpiredContent())


def remove_expired_data(provider):
    """Remove expired data for provider"""
    logger.info('Removing expired content for provider: %s' % provider.get('_id', 'Detached items'))

    try:
        feeding_service = registered_feeding_services[provider['feeding_service']]
        feeding_service = feeding_service.__class__()
        ingest_collection = feeding_service.service if hasattr(feeding_service, 'service') else 'ingest'
    except KeyError:
        ingest_collection = 'ingest'

    ingest_service = superdesk.get_resource_service(ingest_collection)

    items = get_expired_items(provider, ingest_collection)

    ids = [item['_id'] for item in items]
    items.rewind()
    file_ids = [rend.get('media')
                for item in items
                for rend in item.get('renditions', {}).values()
                if not item.get('archived') and rend.get('media')]

    if ids:
        logger.info('Removing items %s' % ids)
        ingest_service.delete({'_id': {'$in': ids}})
        push_expired_notification(ids)

    for file_id in file_ids:
        logger.info('Deleting file: %s' % file_id)
        superdesk.app.media.delete(file_id)

    logger.info('Removed expired content for provider: {0} count: {1}'
                .format(provider.get('_id', 'Detached items'), len(ids)))

    remove_expired_from_elastic(ingest_collection)


def remove_expired_from_elastic(ingest_collection):
    """Remove expired items from elastic which shouldn't be there anymore - expired before previous run."""
    ingest = superdesk.get_resource_service(ingest_collection)
    items = ingest.search({'filter': {'range': {'expiry': {'lt': 'now-5m/m'}}}})
    if items.count():
        logger.warning('there are expired items in elastic (%d)' % (items.count(), ))
        for item in items:
            logger.debug('doc only in elastic item=%s' % (item, ))
            ingest.remove_from_search(item)


def get_expired_items(provider_id, ingest_collection):
    query_filter = get_query_for_expired_items(provider_id)
    return superdesk.get_resource_service(ingest_collection).get_from_mongo(lookup=query_filter, req=None)


def get_query_for_expired_items(provider):
    """Find all ingest items with given provider id and expiry is past

    :param dict provider: ingest provider
    :return str: mongo query
    """
    query = {'expiry': {'$lte': utcnow()}}

    if provider.get('_id'):
        query['ingest_provider'] = str(provider.get('_id'))

    if provider.get('exclude'):
        excluded = provider.get('exclude')
        query['ingest_provider'] = {'$nin': excluded}

    return query
