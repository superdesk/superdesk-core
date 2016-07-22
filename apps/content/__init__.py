"""Content related helpers and utils.
"""

from eve.utils import config
from superdesk.notification import push_notification
from apps.auth import get_user


def push_content_notification(items, event='content:update'):
    """Push content:update notification for multiple items.

    It can be also 2 versions of same item in updated handler
    so that we sent event with both old and new desk/stage.

    :param list items: list of items
    :param event: custom event name
    """
    ids = {}
    desks = {}
    stages = {}
    for item in items:
        ids[str(item.get('_id', ''))] = 1
        task = item.get('task', {})
        if task.get('desk'):
            desks[str(task.get('desk', ''))] = 1
        if task.get('stage'):
            stages[str(task.get('stage', ''))] = 1
    user = get_user()
    push_notification(
        event,
        user=str(user.get(config.ID_FIELD, '')),
        items=ids,
        desks=desks,
        stages=stages
    )


def push_item_move_notification(original, doc, event='item:move'):
    """Push item:move notification.

    :param original: original doc
    :param doc: doc after updates
    :param event: event name
    """
    from_task = original.get('task', {})
    to_task = doc.get('task', {})
    user = get_user()
    push_notification(
        event,
        user=str(user.get(config.ID_FIELD, '')),
        item=str(original.get(config.ID_FIELD)),
        item_version=str(original.get(config.VERSION)),
        from_desk=str(from_task.get('desk')),
        from_stage=str(from_task.get('stage')),
        to_desk=str(to_task.get('desk')),
        to_stage=str(to_task.get('stage'))
    )


def push_expired_notification(ids, event='item:expired'):
    """Push item:expired notification.

    :param ids: list of expired item ids
    :param event: event name
    """
    push_notification(
        event,
        items={str(_id): 1 for _id in ids}
    )
