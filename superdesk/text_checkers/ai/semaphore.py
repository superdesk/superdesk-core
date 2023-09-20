import os
import logging
import requests
import xml.etree.ElementTree as ET
from flask import current_app, abort, jsonify
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

    # Set the values of environment variables directly within the class
    base_url = "https://ca.cloud.smartlogic.com/token"  
    analyze_url = "https://ca.cloud.smartlogic.com/svc/5457e590-c2cc-4219-8947-e7f74c8675be/?operation=classify"  
    api_key = "OoP3QRRkLVCzo4sRa6iAyg==" 

    
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
        try:
            if not self.base_url or not self.api_key:
                logger.warning("Semaphore is not configured properly, can't analyze content")
                abort(500, description="Semaphore is not configured properly, can't analyze content")

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
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Semaphore request failed: {str(e)}")
            abort(500, description=f"Semaphore request failed: {str(e)}")
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            abort(500, description=f"An error occurred: {str(e)}")

    
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
