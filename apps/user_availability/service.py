import superdesk


from apps.auth import get_user_id


class AvailabilityService(superdesk.Service):
    def on_create(self, docs):
        for doc in docs:
            doc["user"] = get_user_id()
