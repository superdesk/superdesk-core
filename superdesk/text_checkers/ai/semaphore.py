import os
import logging
import requests
import xml.etree.ElementTree as ET
from flask import current_app, abort
from .base import AIServiceBase
import traceback



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
            # logger.info("HTML INPUT")
            # logger.info(html_content)
            # logger.info(type(html_content))

            xml_payload = self.html_to_xml(html_content)  # Define this method to convert HTML to XML
            
            # logger.info("xml payload from html_to_xml ")
            # logger.info(xml_payload)

            # Make a POST request using XML payload
            headers = {
                "Authorization": f"bearer {self.get_access_token()}"
            }

            try:
                        
                payload = {'XML_INPUT': xml_payload}

                # payload = f"{{'XML_INPUT': '{xml_payload}'}}"

                # logger.info(payload)
                
            except Exception as e:
                traceback.print_exc()
                logger.error(f"An error occurred. We are inputting payload: {str(e)}")
        
            try:
                response = session.post(self.analyze_url, headers=headers, data=payload)
                logger.info(response.text)
            
            except Exception as e:
                traceback.print_exc()
                logger.error(f"An error occurred. We are making the request: {str(e)}")
        
            response.raise_for_status()

            logger.info("Response Content")
            logger.info(response.text)

            
            def transform_xml_response(xml_data):
                # Parse the XML data
                root = ET.fromstring(xml_data)
            
                # Initialize a dictionary to hold the transformed data
                response_dict = {
                    "subject": [],
                    "organisation": [],
                    "person": [],
                    "event": [],
                    "place": [],
                    "object": []
                }
            
                # Iterate through the XML elements and populate the dictionary
                for element in root.iter():
                    if element.tag == "META":
                        meta_name = element.get("name")
                        meta_value = element.get("value")
                        meta_score = element.get("score", "0.0")  # Default score if not present
            
                        # Determine the appropriate group based on the meta name
                        group = None
                        if meta_name == "TEXTMINE_Organization":
                            group = "organisation"
                        elif meta_name == "TEXTMINE_Person":
                            group = "person"
                        elif meta_name == "Event":
                            group = "event"
                        elif meta_name == "Media Topic":
                            group = "place"  # Assuming "Media Topic" corresponds to "place"
            
                        if group:
                            tag_data = {
                                "name": meta_value,
                                "qcode": meta_score,  # Use score as a temporary qcode
                                "source": "source_value",  # You can replace with actual source value
                                "altids": {"source_name": "source_id"},  # Replace with actual source name and id
                                "aliases": [],  # You can add aliases if available
                                "original_source": "original_source_value",  # Replace with actual original source value
                                "scheme": "scheme_value",  # Replace with actual scheme value
                            }
            
                            response_dict[group].append(tag_data)
            
                return response_dict


            
          
        
            root = response.text
            
            json_response = transform_xml_response(root)  # Define this method to convert XML to JSON

            logger.info("JSON Payload from transform_xml_response ")
            logger.info(json_response)

            dummy_tag_data = {
                "name": "Sample Concept",
                "qcode": "12345-67890",
                "parent": "Parent Concept",
                "source": "imatrics",
                "aliases": ["Alias1", "Alias2"],
                "original_source": "Original Source",
                "altids": {
                    "imatrics": "12345-67890"
                }
            }

            
            return dummy_tag_data
            
        except requests.exceptions.RequestException as e:  
            traceback.print_exc()
            logger.error(f"Semaphore request failed. We are in analyze RequestError exception: {str(e)}")
              
        except Exception as e:
            traceback.print_exc()
            logger.error(f"An error occurred. We are in analyze exception: {str(e)}")
            
    

    def html_to_xml(self, html_content: str) -> str:
        
        def clean_html_content(input_str):
            # Remove full HTML tags using regular expressions
            your_string = input_str.replace('<p>', '')
            your_string = your_string.replace('</p>', '')
            
            return your_string


        
        try:
            # Extract 'body_html' from the HTML content
            
    
            # Create the XML template with triple-quotes for multi-line content
            xml_template = """<?xml version="1.0" ?>
            <request op="CLASSIFY">
                <document>
                    <body>{}</body>
                </document>
            </request>
            """

            
            body_html = html_content['body_html']
            body_html = clean_html_content(body_html)
            
            # Embed the 'body_html' into the XML template
            xml_output = xml_template.format(body_html)
    
            return xml_output
    
        except Exception as e:
            traceback.print_exc()
            logger.error(f"An error occurred in html_to_xml: {str(e)}")

    
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
