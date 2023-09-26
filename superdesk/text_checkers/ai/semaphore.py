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
            logger.info("HTML INPUT")
            logger.info(html_content)
            logger.info(type(html_content))

            xml_payload = self.html_to_xml(html_content)  # Define this method to convert HTML to XML
            
            logger.info("xml payload from html_to_xml ")
            logger.info(xml_payload)

            # Make a POST request using XML payload
            headers = {
                "Authorization": f"bearer {self.get_access_token()}"
            }

            try:
                        
                payload = {'XML_INPUT': xml_payload}

            except Exception as e:
                logger.error(f"An error occurred. We are inputting payload: {str(e)}")
        
            try:
                response = session.post(self.analyze_url, headers=headers, data=payload, timeout=TIMEOUT)
                logger.info(response.text)
            
            except Exception as e:
                logger.error(f"An error occurred. We are making the request: {str(e)}")
        
            response.raise_for_status()

            logger.info("Response Content")
            logger.info(response.text)

            
            # Convert XML response to JSON
            xml_dummy = response.text
            logger.error(xml_dummy)
            root = ET.fromstring(xml_dummy.strip())
            
            logger.info("XML Output from API")
            logger.info(root)
            

            
            def xml_to_json(element: ET.Element) -> dict:
                """Convert XML Element to JSON."""
                try:
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
                    
                except Exception as e:
                    logger.error(f"An error occurred. We are in xml_to_json exception: {str(e)}")
        

            
            json_response = xml_to_json(root)  # Define this method to convert XML to JSON

            return json_response
            
        except requests.exceptions.RequestException as e:  
            logger.error(f"Semaphore request failed. We are in analyze RequestError exception: {str(e)}")
              
        except Exception as e:
            logger.error(f"An error occurred. We are in analyze exception: {str(e)}")
            
    

    # def html_to_xml(self, html_content: str) -> str:
    #     # Create the root element

    #     try:
    #         root = ET.Element("request")
    #         root.set("op", "CLASSIFY")
        
    #         # Create the document element
    #         document = ET.SubElement(root, "document")
        
    #         # Create the body element
    #         body = ET.SubElement(document, "body")
        
    #         # Set the text of the body element to the HTML content
    #         body.text = html_content
        
    #         # Convert the XML tree to a string
    #         xml_output = ET.tostring(root, encoding="utf-8", method="xml").decode("utf-8")

    #     except Exception as e:
    #             logger.error(f"An error occurred. We are in xml to json: {str(e)}")
        
    #     return xml_output

    def html_to_xml(self, html_content: str) -> str:
        # Create the XML string
        try:
            xml_template = """<?xml version="1.0" ?>
            <request op="CLASSIFY">
                <document>
                    <body_html>{}</body_html>
                </document>
            </request>
            """
            # Embed the HTML content into the XML template
            body_html = html_content['body_html']
            xml_output = xml_template.format(body_html)

        except Exception as e:
            logger.error(f"An error occurred. We are in xml to json: {str(e)}")
            return ""
        
        return xml_output

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
