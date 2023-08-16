from flask import current_app, json

from superdesk.publish import register_transmitter
from superdesk.publish.publish_service import PublishService
from superdesk.text_checkers.ai.imatrics import IMatrics
import logging

logging.basicConfig(level=logging.DEBUG) 
logger = logging.getLogger(__name__)

class IMatricsTransmitter(PublishService):
    def _transmit(self, queue_item, subscriber):
        imatrics = IMatrics(current_app)
        item = json.loads(queue_item["formatted_item"])

        logger.warning("Logging in Transmitter for IMAtrics")
        logging.debug("Transmitting item: %s", item)
        
        imatrics.publish(item)


register_transmitter("imatrics", IMatricsTransmitter(), [])
