import os
import logging
import requests
import xml.etree.ElementTree as ET
from flask import current_app
from superdesk.errors import SuperdeskApiError
from .base import AIServiceBase

logger = logging.getLogger(__name__)
session = requests.Session()

TIMEOUT = (5, 30)

class Semaphore(AIServiceBase):
    """Semaphore autotagging service
    
    Environment variables SEMAPHORE_BASE_URL, SEMAPHORE_ANALYZE_URL, and SEMAPHORE_API_KEY must be set.
    """

    name = "semaphore"
    label = "Semaphore autotagging service"

    @property
    def base_url(self):
        return current_app.config.get("SEMAPHORE_BASE_URL", os.environ.get("SEMAPHORE_BASE_URL"))

    @property
    def analyze_url(self):
        return current_app.config.get("SEMAPHORE_ANALYZE_URL", os.environ.get("SEMAPHORE_ANALYZE_URL"))

    @property
    def api_key(self):
        return current_app.config.get("SEMAPHORE_API_KEY", os.environ.get("SEMAPHORE_API_KEY"))

    def get_access_token(self):
        """Get access token for Semaphore."""
        url = self.base_url
        payload = f'grant_type=apikey&key={self.api_key}'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = session.post(url, headers=headers, data=payload, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json().get("access_token")

  
    def analyze(self, html_content: str) -> dict:
        """Analyze HTML content to get tagging suggestions using Semaphore."""
        if not self.base_url or not self.api_key:
            logger.warning("Semaphore is not configured properly, can't analyze content")
            return {}

        # Convert HTML to XML
        xml_payload = self.html_to_xml(html_content)  # Define this method to convert HTML to XML

        # Make a POST request using XML payload
        headers = {
            "Authorization": f"bearer {self.get_access_token()}"
        }
        response = session.post(self.analyze_url, headers=headers, data=xml_payload, timeout=TIMEOUT)
        response.raise_for_status()

        # Convert XML response to JSON
        json_response = self.xml_to_json(response.text)  # Define this method to convert XML to JSON

        return json_response

    def html_to_xml(self, html_content: str) -> str:
        """Convert HTML content to XML. This needs to be defined based on the required format."""
        # TODO: Add conversion logic here
        return ""

    def xml_to_json(self, xml_content: str) -> dict:
        """Convert XML content to JSON."""
        root = ET.fromstring(xml_content)
        # Conversion logic to be added here based on the XML structure
        # For simplicity, this is a basic example and might not work for complex XML structures
        json_data = {}
        for child in root:
            json_data[child.tag] = child.text
        return json_data


def init_app(app):
    Semaphore(app)
