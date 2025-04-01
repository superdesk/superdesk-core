import superdesk
from superdesk.notification import push_notification
from apps.auth import get_user_id


class AvailabilityService(superdesk.Service):
    def on_create(self, docs):
        for doc in docs:
            doc["user"] = get_user_id()


class DefaultAvailabilityService(superdesk.Service):
    """Service class for the default user availability resource."""

    def on_created(self, docs):
        """Event handler for created event."""
        for doc in docs:
            push_notification("default_user_availability:created", item=str(doc.get("_id")))

    def on_updated(self, updates, original):
        """Event handler for updated event."""
        push_notification("default_user_availability:updated", item=str(original.get("_id")))

    def on_deleted(self, doc):
        """Event handler for deleted event."""
        push_notification("default_user_availability:deleted", item=str(doc.get("_id")))
