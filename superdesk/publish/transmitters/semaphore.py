from flask import current_app, json

from superdesk.publish import register_transmitter
from superdesk.publish.publish_service import PublishService
from superdesk.text_checkers.ai.semaphore import Semaphore  # Import the Semaphore integration class

class SemaphoreTransmitter(PublishService):
    def _transmit(self, queue_item, subscriber):
        semaphore = Semaphore(current_app)  # Initialize the Semaphore integration
        item = json.loads(queue_item["formatted_item"])
        # Modify this part to transmit the item using the Semaphore integration
        semaphore.transmit(item)

# Register the Semaphore transmitter
register_transmitter("semaphore", SemaphoreTransmitter(), [])
