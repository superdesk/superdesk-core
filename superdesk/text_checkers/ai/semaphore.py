import os
import logging
import requests
import xml.etree.ElementTree as ET
from flask import current_app, abort
from .base import AIServiceBase
import traceback
import io
import json



logger = logging.getLogger(__name__)
session = requests.Session()

TIMEOUT = (5, 30)


class Semaphore(AIServiceBase):
    """Semaphore autotagging service
    
    Environment variables SEMAPHORE_BASE_URL, SEMAPHORE_ANALYZE_URL, and SEMAPHORE_API_KEY must be set.
    """

    name = "semaphore"
    label = "Semaphore autotagging service"
    print(AIServiceBase)


	
	
    def __init__(self,data):

        self.base_url = "https://ca.cloud.smartlogic.com/token"  
        self.analyze_url = "https://ca.cloud.smartlogic.com/svc/5457e590-c2cc-4219-8947-e7f74c8675be/?operation=classify"
        # self.analyze_url = "https://ca.cloud.smartlogic.com/svc/5457e590-c2cc-4219-8947-e7f74c8675be/"  
        self.api_key = "OoP3QRRkLVCzo4sRa6iAyg=="
        self.search_url = "https://ca.cloud.smartlogic.com/svc/5457e590-c2cc-4219-8947-e7f74c8675be/SES//CPKnowledgeSystem/en/hints/"

        

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

    
    def analyze_2(self, html_content: str) -> dict:
        try:
            if not self.base_url or not self.api_key:
                logger.warning("Semaphore Search is not configured properly, can't analyze content")
                return {}
            
            print(html_content['searchString'])
            query = html_content['searchString']
            
            new_url = self.search_url+query+".json"

            # Make a POST request using XML payload
            headers = {
                "Authorization": f"bearer {self.get_access_token()}"
            }

            
            try:
                response = session.get(new_url, headers=headers)
                print('response is')
                print(response)

                response.raise_for_status()
            except Exception as e:
                traceback.print_exc()
                logger.error(f"An error occurred while making the request: {str(e)}")

            root = response.text
            print('Root is')
            print(root)

            print(type(root))

          

            # def transform_xml_response(xml_data):
            def transform_xml_response(api_response):
                # Initialize the result dictionary
                result = {
                    "subject": [],
                    "organisation": [],
                    "person": [],
                    "event": [],
                    "place": []
                }

                # Iterate through the termHints in the API response
                for item in api_response["termHints"]:
                    entry = {
                        "name": item["name"],
                        "qcode": item["id"],
                        "source": "Semaphore",  # Replace with actual source if available
                        "altids": {"source_name": "source_id"},  # Replace with actual source name and id
                        "original_source": "original_source_value",  # Replace with actual original source value
                        "scheme": "http://cv.cp.org/"  # Replace with actual scheme value
                    }

                    # Check the classes and add to the appropriate category
                    if "Organization" in item["classes"]:
                        result["organisation"].append(entry)
                    elif "People" in item["classes"]:
                        result["person"].append(entry)
                    elif "Event" in item["classes"]:
                        result["event"].append(entry)
                    elif "Place" in item["classes"]:
                        result["place"].append(entry)
                    else:
                        entry["scheme"] = "media topics"
                        result["subject"].append(entry)

                return result
                              
                
            # root = root.replace('<?xml version="1.0" encoding="UTF-8"?>','')
            root = json.loads(root)
            json_response = transform_xml_response(root)

            print('Json Response is ')
            print(json_response)


            return json_response
        
        except requests.exceptions.RequestException as e:
            traceback.print_exc()
            logger.error(f"Semaphore Search request failed. We are in analyze RequestError exception: {str(e)}")


    def analyze(self, html_content: str) -> dict:
        try:
            if not self.base_url or not self.api_key:
                logger.warning("Semaphore is not configured properly, can't analyze content")
                return {}
            
            try:
                for key,value in html_content.items():
                    if key == 'searchString':
                        print('______________________________________---------------------------------------')
                        print('Running for Search')
                        print(value)
                        self.output = self.analyze_2(html_content)
                        return self.output
                    else:
                        print('###########################################################################')
            except TypeError:
                pass

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

            


            

            def transform_xml_response(xml_data):
                # Parse the XML data
                root = ET.fromstring(xml_data)

                # Initialize a dictionary to hold the transformed data
                response_dict = {
                    "subject": [],
                    "organisation": [],
                    "person": [],
                    "event": [],
                    "place": []                   
                }

                # Temporary storage for path labels and GUIDs
                path_labels = {}
                path_guids = {}

                # Helper function to add data to the dictionary if it's not a duplicate and has a qcode
                def add_to_dict(group, tag_data):
                    if tag_data["qcode"] and tag_data not in response_dict[group]:
                        response_dict[group].append(tag_data)

                # Iterate through the XML elements and populate the dictionary
                for element in root.iter():
                    if element.tag == "META":
                        meta_name = element.get("name")
                        meta_value = element.get("value")
                        meta_score = element.get("score")
                        meta_id = element.get("id")

                        # Process 'Media Topic_PATH_LABEL' and 'Media Topic_PATH_GUID'
                        if meta_name == "Media Topic_PATH_LABEL":
                            path_labels[meta_score] = meta_value.split("/")[1:]
                        elif meta_name == "Media Topic_PATH_GUID":
                            path_guids[meta_score] = meta_value.split("/")[1:]

                        # Process other categories
                        else:
                            group = None
                            if "Organization" in meta_name:
                                group = "organisation"
                            elif "Person" in meta_name:
                                group = "person"
                            elif "Event" in meta_name:
                                group = "event"
                            elif "Place" in meta_name:
                                group = "place"

                            if group:
                                tag_data = {
                                    "name": meta_value,
                                    "qcode": meta_id if meta_id else "",
                                    "source": "source_value",
                                    "altids": {"source_name": "source_id"},
                                    "original_source": "original_source_value",
                                    "scheme": "http://cv.cp.org/"
                                }
                                add_to_dict(group, tag_data)

                # Match path labels with path GUIDs based on scores
                for score, labels in path_labels.items():
                    guids = path_guids.get(score, [])
                    if len(labels) != len(guids):
                        continue  # Skip if there's a mismatch in the number of labels and GUIDs

                    parent_qcode = None  # Track the parent qcode
                    for label, guid in zip(labels, guids):
                        tag_data = {
                            "name": label,
                            "qcode": guid,
                            "parent": parent_qcode,
                            "source": "source_value",
                            "altids": {"source_name": "source_id"},
                            "original_source": "original_source_value",
                            "scheme": "media topics"
                        }
                        add_to_dict("subject", tag_data)
                        parent_qcode = guid  # Update the parent qcode for the next iteration

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
            your_string = your_string.replace('&nbsp;', '')
            your_string = your_string.replace('&amp;', '')
            your_string = your_string.replace('&lt;&gt;', '')
            # your_string = your_string.replace('&lt;', '')
            # your_string = your_string.replace('&gt;', '')
            

            
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
    print(type(app))
    print(app)
    a = Semaphore(app)
    return a.output
