from superdesk.celery_app import celery
from .remove_expired_items import RemoveExpiredItems


@celery.task(soft_time_limit=600)
def item_expiry():
    RemoveExpiredItems().run()
