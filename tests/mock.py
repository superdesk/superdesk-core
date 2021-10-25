from unittest.mock import create_autospec

from superdesk.publish.subscribers import SubscribersService


subscriber_service = create_autospec(SubscribersService)
subscriber_service.generate_sequence_number.return_value = 100


class Resource:
    def __init__(self, service):
        self.service = service


resources = {
    "subscribers": Resource(subscriber_service),
}
