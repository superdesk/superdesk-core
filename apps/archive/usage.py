
import bson
import logging
import superdesk

from superdesk.utc import utcnow
from superdesk.metadata.item import ITEM_STATE, PUBLISH_STATES


logger = logging.getLogger(__name__)


def track_usage(media_item, stored_item, item_obj, item_name, original):
    if not media_item:
        return

    try:
        orig_id = original['associations'][item_name]['_id']
    except (AttributeError, TypeError, KeyError):
        orig_id = None

    if item_obj['_id'] != orig_id:
        _update_usage(media_item)
        stored_item['used'] = True


def _update_usage(item):
    updates = {
        'used': True,
        'used_count': item.get('used_count', 0) + 1,
        'used_updated': utcnow(),
    }

    superdesk.get_resource_service('archive').system_update(item['_id'], updates, item)

    # update published item state as well
    if item.get(ITEM_STATE) in PUBLISH_STATES:
        published = superdesk.get_resource_service('published').get_last_published_version(item['_id'])
        if published:
            superdesk.get_resource_service('published').system_update(bson.ObjectId(published['_id']),
                                                                      updates, published)
        else:
            logger.warning('published item not found for item %s', item['_id'])

    item.update(updates)


def update_refs(updates, original):
    """Update refs stored on item based on its associations.

    We can't use associations for queries due to unknown keys in dict,
    so storing basic metadata again as list in `refs`.
    """
    if 'associations' not in updates:
        return
    refs = []
    assoc = original['associations'].copy() if original.get('associations') else {}
    assoc.update(updates['associations'] or {})
    for key, val in assoc.items():
        if not val:
            continue
        if val.get('_id') and not val.get('guid'):
            # for related items we only store the _id, fetch other metadata
            item = superdesk.get_resource_service('archive').find_one(req=None, _id=val['_id']) or {}
        else:
            item = {}
        refs.append({
            'key': key,
            '_id': val.get('_id'),
            'uri': val.get('uri') or item.get('uri'),
            'guid': val.get('guid') or item.get('guid'),
            'type': val.get('type') or item.get('type'),
        })
    updates['refs'] = refs
