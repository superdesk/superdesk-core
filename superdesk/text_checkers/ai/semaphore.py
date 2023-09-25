import os
import logging
import requests
import xml.etree.ElementTree as ET
from flask import current_app, abort
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



    def __init__(self,data):

        self.base_url = "https://ca.cloud.smartlogic.com/token"  
        self.analyze_url = "https://ca.cloud.smartlogic.com/svc/5457e590-c2cc-4219-8947-e7f74c8675be/?operation=classify"  
        self.api_key = "ota1b5FACNdPLEAo8Ue8Hg=="   

        self.session = requests.Session()  
        self.TIMEOUT = 10 
        self.logger = logging.getLogger(__name__) 
        
        self.output = self.analyze(data)
        
    
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
            logger.error(f"Semaphore request failed. We are in analyze RequestError exception: {str(e)}")
            abort(500, description=f"Semaphore request failed. We are in analyze RequestError exception: {str(e)}")
        
        except Exception as e:
            logger.error(f"An error occurred. We are in analyze exception: {str(e)}")
            abort(500, description=f"An error occurred.We are in analyze exception: {str(e)}")

    
    def html_to_xml(self, html_content: str) -> str:
        """Convert HTML content to XML."""
        xml_string = '<?xml version="1.0" ?>\n<request op="CLASSIFY">\n'
        
        # Extract title content
        title_start = html_content.find('<title>') + len('<title>')
        title_end = html_content.find('</title>')
        if title_start != -1 and title_end != -1:
            title_content = html_content[title_start:title_end].strip()
            xml_string += f'  <document>\n    <title>{title_content}</title>\n'
        else:
            xml_string += '  <document>\n    <title></title>\n'
        
        # Extract body content
        body_start = html_content.find('<body>') + len('<body>')
        body_end = html_content.find('</body>')
        if body_start != -1 and body_end != -1:
            body_content = html_content[body_start:body_end].strip()
            xml_string += f'    <body>{body_content}</body>\n  </document>\n  <multiarticle />\n</request>'
        else:
            xml_string += '    <body></body>\n  </document>\n  <multiarticle />\n</request>'
        
        return xml_string

    
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
    a = Semaphore(app)
    return a.output
