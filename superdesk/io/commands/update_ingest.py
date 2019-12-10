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
from datetime import timedelta, timezone, datetime

from flask import current_app as app
from werkzeug.exceptions import HTTPException

import superdesk
from superdesk.activity import ACTIVITY_EVENT, notify_and_add_activity
from superdesk.celery_app import celery
from superdesk.celery_task_utils import get_lock_id
from superdesk.errors import ProviderError
from superdesk.io import get_feeding_service
from superdesk.io.registry import registered_feeding_services, registered_feed_parsers
from superdesk.io.iptc import subject_codes
from superdesk.lock import lock, unlock
from superdesk.media.renditions import update_renditions, transfer_renditions
from superdesk.metadata.item import GUID_NEWSML, GUID_FIELD, FAMILY_ID, ITEM_TYPE, CONTENT_TYPE, CONTENT_STATE, \
    ITEM_STATE
from superdesk.metadata.utils import generate_guid
from superdesk.notification import push_notification
from superdesk.utc import utcnow, get_expiry_date
from superdesk.workflow import set_default_state
from superdesk.errors import IngestFileError
from copy import deepcopy

UPDATE_SCHEDULE_DEFAULT = {'minutes': 5}
LAST_UPDATED = 'last_updated'
LAST_INGESTED_ID = 'last_ingested_id'
LAST_ITEM_UPDATE = 'last_item_update'
IDLE_TIME_DEFAULT = {'hours': 0, 'minutes': 0}

UPDATE_TTL = 1800

logger = logging.getLogger(__name__)


def is_service_and_parser_registered(provider):
    """Tests if the Feed Service and Feed Parser associated with are registered with application.

    :param provider:
    :type provider: dict :py:class:`superdesk.io.ingest_provider_model.IngestProviderResource`
    :return: True if both Feed Service and Feed Parser are registered. False otherwise.
    :rtype: bool
    """
    return provider.get('feeding_service') in registered_feeding_services and \
        provider.get('feed_parser') is None or provider.get('feed_parser') in registered_feed_parsers


def is_scheduled(provider):
    """Test if given provider should be scheduled for update.

    :param provider: ingest provider
    """
    now = utcnow()
    last_updated = provider.get(LAST_UPDATED, now - timedelta(days=100))  # if never updated run now
    update_schedule = provider.get('update_schedule', UPDATE_SCHEDULE_DEFAULT)
    return last_updated + timedelta(**update_schedule) < now


def is_closed(provider):
    """Test if provider is closed.

    :param provider: ingest provider
    """
    return provider.get('is_closed', False)


def is_not_expired(item, delta):
    if item.get('expiry') or item.get('versioncreated'):
        try:
            expiry = item.get('expiry', item['versioncreated'] + delta)
        except OverflowError:  # this will never expire
            return True
        if expiry.tzinfo:
            return expiry > utcnow()
        else:
            return expiry > datetime.now()
    if not item.get('versioncreated'):  # can't say really
        return True
    return False


def filter_expired_items(provider, items):
    """Filter out expired items from the list of articles to be ingested.

    Filte both expired and `item['type'] not in provider['content_types']`.

    :param provider: Ingest Provider Details.
    :type provider: dict :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
    :param items: list of items received from the provider
    :type items: list
    :return: list of items which can be saved into ingest collection
    :rtype: list
    """
    try:
        try:
            content_expiry = int(provider['content_expiry'])
        except ValueError:
            logger.warning('invalid content_expiry: content_expiry={value}'.format(
                value=provider['content_expiry']))
            del provider['content_expiry']
            content_expiry = None
        except (TypeError, KeyError):
            content_expiry = None
        else:
            if content_expiry < 0:
                del provider['content_expiry']
                content_expiry = None

        delta = timedelta(minutes=content_expiry or app.config['INGEST_EXPIRY_MINUTES'])
        filtered_items = [item for item in items if is_not_expired(item, delta) and
                          item.get(ITEM_TYPE, 'text') in provider.get('content_types', [])]

        if len(items) != len(filtered_items):
            logger.warning('Received {0} articles from provider {1}, but only {2} are eligible to be saved in ingest'
                           .format(len(items), provider['name'], len(filtered_items)))

        return filtered_items
    except Exception as ex:
        raise ProviderError.providerFilterExpiredContentError(ex, provider)


def get_provider_rule_set(provider):
    if provider.get('rule_set'):
        return superdesk.get_resource_service('rule_sets').find_one(_id=provider['rule_set'], req=None)


def get_provider_routing_scheme(provider):
    """Returns the ingests provider's routing scheme configuration.

    If provider has a routing scheme defined (i.e. scheme ID is not None), the
    scheme is fetched from the database. If not, nothing is returned.

    For all scheme rules that have a reference to a content filter defined,
    that filter's configuration is fetched from the database as well and
    embedded into the corresponding scheme rule.

    :param dict provider: ingest provider configuration

    :return: fetched provider's routing scheme configuration (if any)
    :rtype: dict or None
    """
    if not provider.get('routing_scheme'):
        return None

    schemes_service = superdesk.get_resource_service('routing_schemes')
    filters_service = superdesk.get_resource_service('content_filters')

    scheme = schemes_service.find_one(_id=provider['routing_scheme'], req=None)
    if not scheme:
        return None

    # for those routing rules that have a content filter defined,
    # get that filter from DB and embed it into the rule...
    rules_filters = (
        (rule, str(rule['filter']))
        for rule in scheme['rules'] if rule.get('filter'))

    for rule, filter_id in rules_filters:
        content_filter = filters_service.find_one(_id=filter_id, req=None)
        rule['filter'] = content_filter

    return scheme


def get_task_ttl(provider):
    update_schedule = provider.get('update_schedule', UPDATE_SCHEDULE_DEFAULT)
    ttl = (update_schedule.get('minutes', 0) * 60 +
           update_schedule.get('hours', 0) * 3600 +
           update_schedule.get('seconds', 0)
           )
    if ttl < 15:
        ttl = 15
    return ttl


def get_is_idle(provider):
    last_item = provider.get(LAST_ITEM_UPDATE)
    idle_time = provider.get('idle_time', IDLE_TIME_DEFAULT)
    if isinstance(idle_time['hours'], datetime):
        idle_hours = 0
    else:
        idle_hours = idle_time['hours']
    if isinstance(idle_time['minutes'], datetime):
        idle_minutes = 0
    else:
        idle_minutes = idle_time['minutes']
    # there is an update time and the idle time is none zero
    if last_item and (idle_hours != 0 or idle_minutes != 0):
        if utcnow() > last_item + timedelta(hours=idle_hours, minutes=idle_minutes):
            return True
    return False


def get_task_id(provider):
    return 'update-ingest-{0}-{1}'.format(provider.get('name'), provider.get(superdesk.config.ID_FIELD))


class UpdateIngest(superdesk.Command):
    """Runs update for ingest providers.

    Example:
    ::

        $ python manage.py ingest:update
        $ python manage.py ingest:update --provider=aap-demo

    """

    option_list = (
        superdesk.Option('--provider', '-p', dest='provider_name'),
        superdesk.Option('--sync', '-s', dest='sync', action='store_true'),
    )

    def run(self, provider_name=None, sync=False):
        lookup = {} if not provider_name else {'name': provider_name}
        for provider in superdesk.get_resource_service('ingest_providers').get(req=None, lookup=lookup):
            if not is_closed(provider) and is_service_and_parser_registered(provider) and \
                    (is_scheduled(provider) or sync):
                kwargs = {
                    'provider': provider,
                    'rule_set': get_provider_rule_set(provider),
                    'routing_scheme': get_provider_routing_scheme(provider),
                    'sync': sync,
                }

                if sync:
                    update_provider.apply(kwargs=kwargs)
                else:
                    update_provider.apply_async(expires=get_task_ttl(provider), kwargs=kwargs, serializer="eve/json")


def update_last_item_updated(update, items):
    if items:
        last_item_update = max(
            [item['versioncreated'] for item in items if item.get('versioncreated')],
            default=utcnow()
        )
        if not update.get(LAST_ITEM_UPDATE) or update[LAST_ITEM_UPDATE] < last_item_update:
            update[LAST_ITEM_UPDATE] = last_item_update


@celery.task(soft_time_limit=UPDATE_TTL)
def update_provider(provider, rule_set=None, routing_scheme=None, sync=False):
    """Fetch items from ingest provider, ingest them into Superdesk and update the provider.

    :param provider: Ingest Provider data
    :param rule_set: Translation Rule Set if one is associated with Ingest Provider.
    :param routing_scheme: Routing Scheme if one is associated with Ingest Provider.
    :param sync: Running in sync mode from cli.
    """
    lock_name = get_lock_id('ingest', provider['name'], provider[superdesk.config.ID_FIELD])

    if not lock(lock_name, expire=UPDATE_TTL + 10):
        if sync:
            logger.error('update is already running for %s', provider['name'])
        return

    try:
        feeding_service = get_feeding_service(provider['feeding_service'])
        update = {LAST_UPDATED: utcnow()}

        if sync:
            provider[LAST_UPDATED] = utcnow() - timedelta(days=9999) # import everything again

        generator = feeding_service.update(provider, update)
        if isinstance(generator, list):
            generator = (items for items in generator)
        failed = None
        while True:
            try:
                items = generator.send(failed)
                failed = ingest_items(items, provider, feeding_service, rule_set, routing_scheme)
                update_last_item_updated(update, items)
            except StopIteration:
                break

        # Some Feeding Services update the collection and by this time the _etag might have been changed.
        # So it's necessary to fetch it once again. Otherwise, OriginalChangedError is raised.
        ingest_provider_service = superdesk.get_resource_service('ingest_providers')
        provider = ingest_provider_service.find_one(req=None, _id=provider[superdesk.config.ID_FIELD])
        ingest_provider_service.system_update(provider[superdesk.config.ID_FIELD], update, provider)

        if LAST_ITEM_UPDATE not in update and get_is_idle(provider):
            admins = superdesk.get_resource_service('users').get_users_by_user_type('administrator')
            notify_and_add_activity(
                ACTIVITY_EVENT,
                'Provider {{name}} has gone strangely quiet. Last activity was on {{last}}',
                resource='ingest_providers', user_list=admins, name=provider.get('name'),
                last=provider[LAST_ITEM_UPDATE].replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%c"))

        logger.info('Provider {0} updated'.format(provider[superdesk.config.ID_FIELD]))

        if LAST_ITEM_UPDATE in update:  # Only push a notification if there has been an update
            push_notification('ingest:update', provider_id=str(provider[superdesk.config.ID_FIELD]))
    except Exception as e:
        logger.error("Failed to ingest file: {error}".format(error=e))
        raise IngestFileError(3000, e, provider)
    finally:
        unlock(lock_name)


def process_anpa_category(item, provider):
    try:
        anpa_categories = superdesk.get_resource_service('vocabularies').find_one(req=None, _id='categories')
        if anpa_categories:
            for item_category in item['anpa_category']:
                mapped_category = [c for c in anpa_categories['items'] if
                                   c['is_active'] is True and item_category['qcode'].lower() == c['qcode'].lower()]
                # if the category is not known to the system remove it from the item
                if len(mapped_category) == 0:
                    item['anpa_category'].remove(item_category)
                else:
                    item_category['name'] = mapped_category[0]['name']
                    # make the case of the qcode match what we hold in our dictionary
                    item_category['qcode'] = mapped_category[0]['qcode']
    except Exception as ex:
        raise ProviderError.anpaError(ex, provider)


def derive_category(item, provider):
    """Assuming that the item has at least one itpc subject use the vocabulary map to derive an anpa category.

    :param item:
    :return: An item with a category if possible
    """
    try:
        categories = []
        subject_map = superdesk.get_resource_service('vocabularies').find_one(req=None, _id='iptc_category_map')
        if subject_map:
            for entry in (map_entry for map_entry in subject_map['items'] if map_entry['is_active']):
                for subject in item.get('subject', []):
                    if subject['qcode'] == entry['qcode']:
                        if not any(c['qcode'] == entry['category'] for c in categories):
                            categories.append({'qcode': entry['category']})
            if len(categories):
                item['anpa_category'] = categories
                process_anpa_category(item, provider)
    except Exception as ex:
        logger.exception(ex)


def process_iptc_codes(item, provider):
    """Ensures that the higher level IPTC codes are present by inserting them if missing.

    For example if given 15039001 (Formula One) make sure that 15039000 (motor racing) and 15000000 (sport)
    are there as well.

    :param item: A story item
    :return: A story item with possible expanded subjects
    """
    try:
        def iptc_already_exists(code):
            for entry in item['subject']:
                if 'qcode' in entry and code == entry['qcode']:
                    return True
            return False

        for subject in item['subject']:
            if 'qcode' in subject and len(subject['qcode']) == 8 and subject['qcode'].isdigit():
                top_qcode = subject['qcode'][:2] + '000000'
                if not iptc_already_exists(top_qcode):
                    try:
                        item['subject'].append({'qcode': top_qcode, 'name': subject_codes[top_qcode]})
                    except KeyError:
                        logger.warning("missing qcode in subject_codes: {qcode}".format(qcode=top_qcode))
                        continue

                mid_qcode = subject['qcode'][:5] + '000'
                if not iptc_already_exists(mid_qcode):
                    try:
                        item['subject'].append({'qcode': mid_qcode, 'name': subject_codes[mid_qcode]})
                    except KeyError:
                        logger.warning("missing qcode in subject_codes: {qcode}".format(qcode=mid_qcode))
                        continue
    except Exception as ex:
        raise ProviderError.iptcError(ex, provider)


def derive_subject(item):
    """Try to derive a subject using the anpa category vocabulary.

    :param item:
    :return:
    """
    try:
        category_map = superdesk.get_resource_service('vocabularies').find_one(req=None, _id='categories')
        if category_map:
            for cat in item['anpa_category']:
                map_entry = next(
                    (code for code in category_map['items'] if code['qcode'] == cat['qcode'] and code['is_active']),
                    None)
                if map_entry and 'subject' in map_entry:
                    item['subject'] = [
                        {'qcode': map_entry.get('subject'), 'name': subject_codes[map_entry.get('subject')]}]
    except Exception as ex:
        logger.exception(ex)


def apply_rule_set(item, provider, rule_set=None):
    """Applies rules set on the item to be ingested into the system.

    If there's no rule set then the item will
    be returned without any change.

    :param item: Item to be ingested
    :param provider: provider object from whom the item was received
    :return: item
    """
    try:
        if rule_set is None and provider.get('rule_set') is not None:
            rule_set = superdesk.get_resource_service('rule_sets').find_one(_id=provider['rule_set'], req=None)

        if rule_set and 'body_html' in item:
            body = item['body_html']

            for rule in rule_set['rules']:
                body = body.replace(rule['old'], rule['new'])

            item['body_html'] = body

        return item
    except Exception as ex:
        raise ProviderError.ruleError(ex, provider)


def ingest_cancel(item, feeding_service):
    """Given an item that has a pubstatus of canceled finds all versions of this item and mark them as canceled as well.

    Uses the URI to identify those items in ingest that are related to this cancellation.

    :param item:
    :return:
    """
    ingest_service = superdesk.get_resource_service(
        feeding_service.service if hasattr(feeding_service, 'service') else 'ingest')
    lookup = {'uri': item.get('uri')}
    family_members = ingest_service.get_from_mongo(req=None, lookup=lookup)
    for relative in family_members:
        update = {'pubstatus': 'canceled', ITEM_STATE: CONTENT_STATE.KILLED}
        ingest_service.patch(relative['_id'], update)


def ingest_items(items, provider, feeding_service, rule_set=None, routing_scheme=None):
    all_items = filter_expired_items(provider, items)
    items_dict = {doc[GUID_FIELD]: doc for doc in all_items}
    items_in_package = []
    failed_items = set()
    created_ids = []
    for item in [doc for doc in all_items if doc.get(ITEM_TYPE) == CONTENT_TYPE.COMPOSITE]:
        items_in_package = [ref['residRef'] for group in item.get('groups', [])
                            for ref in group.get('refs', []) if 'residRef' in ref]

    for item in [doc for doc in all_items if doc.get(ITEM_TYPE) != CONTENT_TYPE.COMPOSITE]:
        ingested, ids = ingest_item(item, provider, feeding_service, rule_set,
                                    routing_scheme=routing_scheme if not item[GUID_FIELD] in items_in_package else None)
        if ingested:
            created_ids = created_ids + ids
        else:
            failed_items.add(item[GUID_FIELD])
    for item in [doc for doc in all_items if doc.get(ITEM_TYPE) == CONTENT_TYPE.COMPOSITE]:
        for ref in [ref for group in item.get('groups', [])
                    for ref in group.get('refs', []) if 'residRef' in ref]:
            if ref['residRef'] in failed_items:
                failed_items.add(item[GUID_FIELD])
                continue

            ref.setdefault('location', 'ingest')
            itemRendition = items_dict.get(ref['residRef'], {}).get('renditions')
            if itemRendition:
                ref.setdefault('renditions', itemRendition)
            ref[GUID_FIELD] = ref['residRef']
            if items_dict.get(ref['residRef']):
                ref['residRef'] = items_dict.get(ref['residRef'], {}).get(superdesk.config.ID_FIELD)
        if item[GUID_FIELD] in failed_items:
            continue
        ingested, ids = ingest_item(item, provider, feeding_service, rule_set, routing_scheme)
        if ingested:
            created_ids = created_ids + ids
        else:
            failed_items.add(item[GUID_FIELD])
    # sync mongo with ingest after all changes
    ingest_collection = feeding_service.service if hasattr(feeding_service, 'service') else 'ingest'
    ingest_service = superdesk.get_resource_service(ingest_collection)
    updated_items = ingest_service.find({'_id': {'$in': created_ids}}, max_results=len(created_ids))
    app.data._search_backend(ingest_collection).bulk_insert(ingest_collection, list(updated_items))
    if failed_items:
        logger.error('Failed to ingest the following items: %s', failed_items)
    return failed_items


def ingest_item(item, provider, feeding_service, rule_set=None, routing_scheme=None):
    items_ids = []
    try:
        ingest_collection = feeding_service.service if hasattr(feeding_service, 'service') else 'ingest'
        ingest_service = superdesk.get_resource_service(ingest_collection)

        # determine if we already have this item
        old_item = ingest_service.find_one(guid=item[GUID_FIELD], req=None)

        if not old_item:
            item.setdefault(superdesk.config.ID_FIELD, generate_guid(type=GUID_NEWSML))
            item[FAMILY_ID] = item[superdesk.config.ID_FIELD]

        item['ingest_provider'] = str(provider[superdesk.config.ID_FIELD])
        item.setdefault('source', provider.get('source', ''))
        item.setdefault('uri', item[GUID_FIELD])  # keep it as original guid
        set_default_state(item, CONTENT_STATE.INGESTED)
        item['expiry'] = get_expiry_date(provider.get('content_expiry') or app.config['INGEST_EXPIRY_MINUTES'],
                                         item.get('versioncreated'))

        if 'anpa_category' in item:
            process_anpa_category(item, provider)

        if 'subject' in item:
            if not app.config.get('INGEST_SKIP_IPTC_CODES', False):
                # FIXME: temporary fix for SDNTB-344, need to be removed once SDESK-439 is implemented
                process_iptc_codes(item, provider)
            if 'anpa_category' not in item:
                derive_category(item, provider)
        elif 'anpa_category' in item:
            derive_subject(item)

        apply_rule_set(item, provider, rule_set)

        if item.get('pubstatus', '') == 'canceled':
            item[ITEM_STATE] = CONTENT_STATE.KILLED
            ingest_cancel(item, feeding_service)

        rend = item.get('renditions', {})
        if rend:
            baseImageRend = rend.get('baseImage') or next(iter(rend.values()))
            if baseImageRend and not baseImageRend.get('media'):  # if there is media should be processed already
                href = feeding_service.prepare_href(baseImageRend['href'], rend.get('mimetype'))
                update_renditions(item, href, old_item)

        # if the item has associated media
        for key, assoc in item.get('associations', {}).items():
            set_default_state(assoc, CONTENT_STATE.INGESTED)
            if assoc.get('renditions'):
                transfer_renditions(assoc['renditions'])
            # wire up the id of the associated feature media to the ingested one
            guid = assoc.get('guid')
            if guid:
                lookup = {'guid': guid}
                ingested = ingest_service.get_from_mongo(req=None, lookup=lookup)
                if ingested.count() >= 1:
                    assoc['_id'] = ingested[0]['_id']
                    for rendition in ingested[0].get('renditions', {}):  # add missing renditions
                        assoc['renditions'].setdefault(
                            rendition,
                            ingested[0]['renditions'][rendition])
                else:  # there is no such item in the system - ingest it
                    status, ids = ingest_item(assoc, provider, feeding_service, rule_set)
                    if status:
                        assoc['_id'] = ids[0]
                        items_ids.extend(ids)
            elif assoc.get('residRef'):
                item['associations'][key] = resolve_ref(assoc)

        new_version = True
        if old_item:
            new_version = is_new_version(item, old_item)
            updates = deepcopy(item)
            ingest_service.patch_in_mongo(old_item[superdesk.config.ID_FIELD], updates, old_item)
            item.update(old_item)
            item.update(updates)
            items_ids.append(item['_id'])
        else:
            if item.get('ingest_provider_sequence') is None:
                ingest_service.set_ingest_provider_sequence(item, provider)
            try:
                items_ids.extend(ingest_service.post_in_mongo([item]))
            except HTTPException as e:
                logger.error('Exception while persisting item in %s collection: %s', ingest_collection, e)
                raise e

        if routing_scheme and new_version:
            routed = ingest_service.find_one(_id=item[superdesk.config.ID_FIELD], req=None)
            superdesk.get_resource_service('routing_schemes').apply_routing_scheme(routed, provider, routing_scheme)

    except Exception as ex:
        logger.exception(ex)
        ProviderError.ingestItemError(ex, provider, item=item)
        return False, []
    return True, items_ids


def resolve_ref(assoc):
    """Resolve reference to existing item."""
    uri = assoc.pop('residRef')
    item = superdesk.get_resource_service('archive').find_one(req=None, uri=uri)
    return item


NEW_VERSION_IGNORE_FIELS = (
    'expiry',
)


def is_new_version(item, old_item):
    # explicit version info
    for field in ('version', 'versioncreated'):
        if item.get(field) and old_item.get(field):
            try:
                return int(item[field], 10) > int(old_item[field], 10)
            except (ValueError, TypeError):
                try:
                    return item[field] > old_item[field]
                except TypeError as ex:
                    logger.exception(ex)
                    # can't compare the values, assuming these are different
                    return True
    # no version info, check content
    for field in item:
        if field in NEW_VERSION_IGNORE_FIELS or item[field] is None:
            continue
        if not old_item.get(field) or item[field] != old_item[field]:
            return True
    return False


superdesk.command('ingest:update', UpdateIngest())
