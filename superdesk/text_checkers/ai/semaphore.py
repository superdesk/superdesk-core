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
        logger.error(data)
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
                
                
            # Convert HTML to XML
            xml_payload = self.html_to_xml(html_content)  # Define this method to convert HTML to XML

            # Make a POST request using XML payload
            headers = {
                "Authorization": f"bearer {self.get_access_token()}"
            }

                        
            payload = {'XML_INPUT': xml_payload}
            
            response = session.post(self.analyze_url, headers=headers, data=payload, timeout=TIMEOUT)
            logger.error(response.text)
            response.raise_for_status()

            # Convert XML response to JSON
            xml_dummy = response.text
            logger.error(xml_dummy)
            root = ET.fromstring(xml_dummy.strip())

            def xml_to_json(element: ET.Element) -> dict:
                """Convert XML Element to JSON."""
                json_data = {}
                if element.attrib:
                    json_data["@attributes"] = element.attrib
                if element.text and element.text.strip():
                    json_data["#text"] = element.text.strip()
                for child in element:
                    child_data = xml_to_json(child)
                    if child.tag in json_data:
                        if not isinstance(json_data[child.tag], list):
                            json_data[child.tag] = [json_data[child.tag]]
                        json_data[child.tag].append(child_data)
                    else:
                        json_data[child.tag] = child_data
                return json_data


            
            json_response = xml_to_json(root)  # Define this method to convert XML to JSON

            return json_response
            
        except requests.exceptions.RequestException as e:  
            logger.error(f"Semaphore request failed. We are in analyze RequestError exception: {str(e)}")
              
        except Exception as e:
            logger.error(f"An error occurred. We are in analyze exception: {str(e)}")
            
    
    def html_to_xml(self, html_content: str) -> str:
        dummy_xml = """<?xml version="1.0" ?><request op="CLASSIFY"><document><title>Test</title><body>This is a test</body></document><multiarticle /></request>"""
        return dummy_xml

    

    # def xml_to_json(self,element: ET.Element) -> dict:
    #     """Convert XML Element to JSON."""
    #     json_data = {}
    #     if element.attrib:
    #         json_data["@attributes"] = element.attrib
    #     if element.text and element.text.strip():
    #         json_data["#text"] = element.text.strip()
    #     for child in element:
    #         child_data = xml_to_json(child)
    #         if child.tag in json_data:
    #             if not isinstance(json_data[child.tag], list):
    #                 json_data[child.tag] = [json_data[child.tag]]
    #             json_data[child.tag].append(child_data)
    #         else:
    #             json_data[child.tag] = child_data
    #     return json_data


def init_app(app):
    a = Semaphore(app)
    return a.output
