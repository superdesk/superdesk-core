import logging
from superdesk.text_utils import get_text
from .ninjs_formatter_2 import NINJSFormatter_2
from superdesk.text_checkers.ai.semaphore import Semaphore  # Import the Semaphore integration class

logger = logging.getLogger(__name__)

class SemaphoreFormatter(NINJSFormatter_2):
    def can_format(self, format_type, article):
        return format_type.lower() == "semaphore" and article.get("type") == "text"

    def _transform_to_ninjs(self, article, subscriber, recursive=True):
        semaphore = Semaphore()  # Initialize the Semaphore integration
        formatted_data = {}  # Define how you want to format the data for Semaphore

        try:
            # Example: format the data
            formatted_data["uuid"] = article["guid"]
            formatted_data["headline"] = get_text(article["headline"])
            # Add more formatting logic here

        except Exception as e:
            logger.error(f"Error formatting data for Semaphore: {str(e)}")
            formatted_data = {}  # Return an empty dictionary in case of an error

        return formatted_data
