import os
import logging
import requests
import xml.etree.ElementTree as ET
from flask import current_app, abort
from .base import AIServiceBase
import traceback
import io



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
        # self.analyze_url = "https://ca.cloud.smartlogic.com/svc/5457e590-c2cc-4219-8947-e7f74c8675be/"  
        self.api_key = "OoP3QRRkLVCzo4sRa6iAyg=="

        

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
                return {}

            # Convert HTML to XML
            xml_payload = self.html_to_xml(html_content)
			
            payload = {'XML_INPUT': xml_payload}

            print("payload is ")
            print(payload)

            # Make a POST request using XML payload
            headers = {
                "Authorization": f"bearer {self.get_access_token()}"
            }

            
            try:
                response = session.post(self.analyze_url, headers=headers, data=payload)
                print('response is')
                print(response)

                response.raise_for_status()
            except Exception as e:
                traceback.print_exc()
                logger.error(f"An error occurred while making the request: {str(e)}")

            root = response.text
            print('Root is')
            print(root)

            


            def transform_xml_response(root):
    # Parse the XML data
                root = ET.fromstring(root)

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

                        meta_id = element.get("id")
                        print(meta_id)

                        # Determine the appropriate group based on the meta name
                        group = None
                        if meta_name == "Organization":
                            group = "organisation"
                        elif meta_name == "Person":
                            group = "person"
                        elif meta_name == "Event":
                            group = "event"
                        elif meta_name == "Place":
                            group = "place"
                        elif meta_name == "Media Topic":
                            group = "object"

                        if group:
                            tag_data = {
                                "name": meta_value,
                                "qcode": meta_id if meta_id else "",  # Use 'id' if available, otherwise an empty string
                                "source": "Semaphore",  # You can replace with actual source value
                                "altids": {"source_name": "source_id"},  # Replace with actual source name and id
                                "original_source": "original_source_value",  # Replace with actual original source value
                                "scheme": "scheme_value",  # Replace with actual scheme value
                            }
                            # Create the category in response_dict if it doesn't exist
                            response_dict.setdefault(group, []).append(tag_data)

                print('response dict is')
                print(response_dict)

                return response_dict
                

               
                
            # root = root.replace('<?xml version="1.0" encoding="UTF-8"?>','')
            json_response = transform_xml_response(root)

            print('Json Response is ')
            print(json_response)


            return json_response

        except requests.exceptions.RequestException as e:
            traceback.print_exc()
            logger.error(f"Semaphore request failed. We are in analyze RequestError exception: {str(e)}")

        except Exception as e:
            traceback.print_exc()
            logger.error(f"An error occurred. We are in analyze exception: {str(e)}")

    
    def html_to_xml(self,html_content: str) -> str: 

        def clean_html_content(input_str):
            # Remove full HTML tags using regular expressions
            your_string = input_str.replace('<p>', '')
            your_string = your_string.replace('</p>', '')
            your_string = your_string.replace('<br>', '')

            
            return your_string    
	   
			
        xml_template = """<?xml version="1.0" ?>
				<request op="CLASSIFY">
				<document>
					<body>&lt;?xml version=&quot;1.0&quot; encoding=&quot;UTF-8&quot;?&gt;
				&lt;story&gt;
					&lt;headline&gt;{}&lt;/headline&gt;
					&lt;headline_extended&gt;{}&lt;/headline_extended&gt;
					&lt;body_html&gt;{}&lt;/body_html&gt; 
                    &lt;slugline&gt;{}&lt;/slugline&gt;                             					
				&lt;/story&gt;
				</body>
				</document>
				</request>
				"""

				
			
			
        body_html = html_content['body_html']
        headline = html_content['headline']
        headline_extended = html_content['abstract']
        slugline = html_content['slugline']
        #  &lt;slugline&gt;{}&lt;/slugline&gt;

				# Embed the 'body_html' into the XML template		
        xml_output = xml_template.format(headline,headline_extended,body_html,slugline)
        xml_output = clean_html_content(xml_output)
            
        return xml_output
		
		
		
        
        
        

    
  


def init_app(app):
    a = Semaphore(app)
    return a.output
