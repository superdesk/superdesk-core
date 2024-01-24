import os
import logging
import requests
import xml.etree.ElementTree as ET
from flask import current_app, abort
from .base import AIServiceBase
import traceback
import io
import json
from requests.exceptions import HTTPError


logger = logging.getLogger(__name__)
session = requests.Session()

TIMEOUT = (5, 30)


class Semaphore(AIServiceBase):
    """Semaphore autotagging service
    
    Environment variables SEMAPHORE_BASE_URL, SEMAPHORE_ANALYZE_URL, SEMAPHORE_SEARCH_URL, SEMAPHORE_GET_PARENT_URL and SEMAPHORE_API_KEY must be set.
    """

    name = "semaphore"
    label = "Semaphore autotagging service"
    print(AIServiceBase)


	
	
    def __init__(self,data):

	# SEMAPHORE_BASE_URL OR TOKEN_ENDPOINT Goes Here
        self.base_url =  os.getenv('SEMAPHORE_BASE_URL')

	#  SEMAPHORE_ANALYZE_URL Goes Here
        self.analyze_url = os.getenv(' SEMAPHORE_ANALYZE_URL')

	#  SEMAPHORE_API_KEY Goes Here
        self.api_key = os.getenv('SEMAPHORE_API_KEY')

	#  SEMAPHORE_SEARCH_URL Goes Here
        self.search_url = os.getenv('SEMAPHORE_SEARCH_URL')

	#  SEMAPHORE_GET_PARENT_URL Goes Here
        self.get_parent_url = os.getenv('SEMAPHORE_GET_PARENT_URL')
    
    #  SEMAPHORE_CREATE_TAG_URL Goes Here
        self.create_tag_url = os.getenv('SEMAPHORE_CREATE_TAG_URL')

	#  SEMAPHORE_CREATE_TAG_TASK Goes Here
        self.create_tag_task = os.getenv('SEMAPHORE_CREATE_TAG_TASK')

    #  SEMAPHORE_CREATE_TAG_QUERY Goes Here
        self.create_tag_query = os.getenv('SEMAPHORE_CREATE_TAG_QUERY')

        
        

        self.output = self.analyze(data)

    
    def convert_to_desired_format(input_data):
        result = {
            "result": {
                "tags": {
                    "subject": input_data['subject'],
                    "organisation": input_data['organisation'],
                    "person": input_data['person'],
                    "event": input_data['event'],
                    "place": input_data['place'],
                    "object": []  # Assuming no data for 'object'
                },
                "broader": {
                    "subject": input_data['broader']
                }
            }
        }

        return result
    
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


    def fetch_parent_info(self,qcode):
    
        headers = {"Authorization": f"Bearer {self.get_access_token()}"}
        try:
            frank = f"?relationshipType=has%20broader"

            query = qcode
            parent_url = self.get_parent_url+query+frank

            response = session.get(parent_url, headers=headers)
            response.raise_for_status()
            root = ET.fromstring(response.text)
            path = root.find(".//PATH[@TYPE='Narrower Term']")
            parent_info = []
            if path is not None:
                for field in path.findall('FIELD'):
                    if field.find('CLASS').get('NAME') == 'Topic':
                        parent_info.append({
                            "name": field.get('NAME'),
                            "qcode": field.get('ID'),
                            "parent": None  # Set to None initially
                        })
            return parent_info, parent_info[::-1]
            
        except Exception as e:
            logger.error(f"Error fetching parent info: {str(e)}")
            return [] 
    
    
    def analyze_parent_info(self, html_content: str) -> dict:
        try:
            if not self.base_url or not self.api_key:
                logger.warning("Semaphore Search is not configured properly, can't analyze content")
                return {}
            
            
            query = html_content['searchString']
            
            new_url = self.search_url+query+".json"

            # Make a POST request using XML payload
            headers = {
                "Authorization": f"bearer {self.get_access_token()}"
            }

            
            try:
                response = session.get(new_url, headers=headers)
                

                response.raise_for_status()
            except Exception as e:
                traceback.print_exc()
                logger.error(f"An error occurred while making the request: {str(e)}")

            root = response.text
            
          

            # def transform_xml_response(xml_data):
            def transform_xml_response(api_response):
                result = {
                    "subject": [],
                    "organisation": [],
                    "person": [],
                    "event": [],
                    "place": [],
                    "broader": []
                }

                # Process each termHint item in the API response
                for item in api_response["termHints"]:
                    
                    scheme_url = "http://cv.cp.org/"

                    if "Organization" in item["classes"]:
                        scheme_url = "http://cv.cp.org/Organizations/"
                        category = "organisation"
                    elif "People" in item["classes"]:
                        scheme_url = "http://cv.cp.org/People/"
                        category = "person"
                    elif "Event" in item["classes"]:
                        scheme_url = "http://cv.cp.org/Events/"
                        category = "event"
                    elif "Place" in item["classes"]:
                        scheme_url = "http://cv.cp.org/Places/"
                        category = "place"
                    else:
                        # For 'subject', a different scheme might be used
                        category = "subject"
                        scheme_url = "http://cv.iptc.org/newscodes/mediatopic/"

                    entry = {
                        "name": item["name"],
                        "qcode": item["id"],
                        "source": "Semaphore",
                        "altids": {"source_name": "source_id"},
                        "original_source": "Semaphore",
                        "scheme": scheme_url,
                        "parent": None  # Initial parent assignment
                    }

                    # Assign to correct category based on class
                    if "Organization" in item["classes"]:
                        result["organisation"].append(entry)
                    elif "People" in item["classes"]:
                        result["person"].append(entry)
                    elif "Event" in item["classes"]:
                        result["event"].append(entry)
                    elif "Place" in item["classes"]:
                        result["place"].append(entry)
                    else:
                        # Fetch parent info for each subject item
                        parent_info, reversed_parent_info = self.fetch_parent_info(item["id"])

                        # Assign the immediate parent to the subject item
                        if parent_info:
                            entry["parent"] = reversed_parent_info[0]["qcode"]  # Immediate parent is the first in the list
                            entry["scheme"] = "http://cv.iptc.org/newscodes/mediatopic/"

                        result["subject"].append(entry)

                        # Process broader items using reversed_parent_info
                        for i in range(len(reversed_parent_info)):
                            broader_entry = {
                                "name": reversed_parent_info[i]["name"],
                                "qcode": reversed_parent_info[i]["qcode"],
                                "parent": reversed_parent_info[i + 1]["qcode"] if i + 1 < len(reversed_parent_info) else None,
                                "source": "Semaphore",
                                "altids": {"source_name": "source_id"},
                                "original_source": "Semaphore",
                                "scheme": "http://cv.iptc.org/newscodes/mediatopic/"
                            }
                            result["broader"].append(broader_entry)

                return result
            

            def convert_to_desired_format(input_data):
                result = {
                    "result": {
                        "tags": {
                            "subject": input_data['subject'],
                            "organisation": input_data['organisation'],
                            "person": input_data['person'],
                            "event": input_data['event'],
                            "place": input_data['place'],
                            "object": []  # Assuming no data for 'object'
                        },
                        "broader": {
                            "subject": input_data['broader']
                        }
                    }
                }

                return result
                            
                            
            
            root = json.loads(root)
            json_response = transform_xml_response(root)          

            json_response = convert_to_desired_format(json_response)

            

            return json_response
        
        except requests.exceptions.RequestException as e:
            traceback.print_exc()
            logger.error(f"Semaphore Search request failed. We are in analyze RequestError exception: {str(e)}")


    def create_tag_in_semaphore(self,html_content: str) -> dict:

        try:
            if not self.create_tag_url or not self.api_key:
                logger.warning("Semaphore Create is not configured properly, can't analyze content")
                return {}
            
            url = self.create_tag_url

            task = self.create_tag_task

            query_string = self.create_tag_query
            
            new_url = url+task+query_string

         

            # Make a POST request using XML payload
            headers = {
                "Authorization": f"bearer {self.get_access_token()}",
                "Content-Type": "application/ld+json"
            }

            manual_tags = extract_manual_tags(html_content["data"])

            for item in manual_tags:
                # print(item)

                concept_name = item["name"]
                scheme = item["scheme"]

                if scheme == "subject":
                    id_value = "http://cv.cp.org/4916d989-2227-4f2d-8632-525cd462ab9f"

                elif scheme == "organization":
                    id_value = "http://cv.cp.org/e2c332d3-05e0-4dcc-b358-9e4855e80e88" 
                
                elif scheme == "places":
                    id_value = "http://cv.cp.org/c3b17bf6-7969-424d-92ae-966f4f707a95" 

                elif scheme =="person":
                    id_value = "http://cv.cp.org/1630a532-329f-43fe-9606-b381330c35cf"
                
                elif scheme == "event":
                    id_value = "http://cv.cp.org/3c493189-023f-4d14-a2f4-fc7b79735ffc"

                


                payload = json.dumps({
                            "@type": [
                                "skos:Concept"
                            ],
                            "rdfs:label": "ConceptNameForUriGeneration",
                            "skos:topConceptOf": {
                                "@id": id_value
                            },
                            "skosxl:prefLabel": [
                                {
                                "@type": [
                                    "skosxl:Label"
                                ],
                                "skosxl:literalForm": [
                                    {
                                    "@value": concept_name,
                                    "@language": "en"
                                    }
                                ]
                                }
                            ]
                            })
                
                try:
                    response = session.post(new_url, headers=headers, data=payload)
                    

                    if response.status_code == 409:
                        print("Tag already exists in KMM. Response is 409 . The Tag is")
                        print(concept_name)
                    else:
                        response.raise_for_status()
                        print('Tag Got Created is ')
                        print(concept_name)
                    

                except HTTPError as http_err:
                    # Handle specific HTTP errors here
                    logger.error(f"HTTP error occurred: {http_err}")
                except Exception as e:
                    traceback.print_exc()
                    logger.error(f"An error occurred while making the create tag request: {str(e)}")

            


        except requests.exceptions.RequestException as e:
            traceback.print_exc()
            logger.error(f"Semaphore Create Tag Failed failed. We are in analyze RequestError exception: {str(e)}")



    def analyze(self, html_content: str) -> dict:
        try:
            if not self.base_url or not self.api_key:
                logger.warning("Semaphore is not configured properly, can't analyze content")
                return {}
            
            try:
                print('Incoming data is')
                print(html_content)

                try:
                    for key,value in html_content.items():
                        if key == 'searchString':
                            print('______________________________________---------------------------------------')
                            print('Running for Search')
                            print(value)
                            self.output = self.analyze_parent_info(html_content)
                            return self.output
                        
                except Exception as e:
                    print(e)
                    pass

                if isinstance(html_content, list):
                    # Iterate over each element in the list
                    for item in html_content:
                        # Check if the item is a dictionary and contains the 'operation' key
                        if isinstance(item, dict) and item.get('operation') == "feedback":
                            print('______________________________________---------------------------------------')
                            print('Running to Create a New Tag in Semaphore')
                            self.output = self.create_tag_in_semaphore(item)
                            return self.output
              
            
                              
            except TypeError:
                pass

            # Convert HTML to XML
            xml_payload = self.html_to_xml(html_content)
			
            payload = {'XML_INPUT': xml_payload}

            

            # Make a POST request using XML payload
            headers = {
                "Authorization": f"bearer {self.get_access_token()}"
            }

            
            try:
                response = session.post(self.analyze_url, headers=headers, data=payload)
                

                response.raise_for_status()
            except Exception as e:
                traceback.print_exc()
                logger.error(f"An error occurred while making the request: {str(e)}")

            root = response.text
            

            


            

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
                                scheme_url = "http://cv.cp.org/Organizations/"
                            elif "Person" in meta_name:
                                group = "person"
                                scheme_url = "http://cv.cp.org/People/"
                            elif "Event" in meta_name:
                                group = "event"
                                scheme_url = "http://cv.cp.org/Events/"
                            elif "Place" in meta_name:
                                group = "place"
                                scheme_url = "http://cv.cp.org/Places/"

                            if group:
                                tag_data = {
                                    "name": meta_value,
                                    "qcode": meta_id if meta_id else "",
                                    "source": "Semaphore",
                                    "altids": {"source_name": "source_id"},
                                    "original_source": "Semaphore",
                                    "scheme": scheme_url
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
                            "source": "Semaphore",
                            "altids": {"source_name": "source_id"},
                            "original_source": "Semaphore",
                            "scheme": "http://cv.iptc.org/newscodes/mediatopic/"
                        }
                        add_to_dict("subject", tag_data)
                        parent_qcode = guid  # Update the parent qcode for the next iteration

                return response_dict
                                          
                
            
            json_response = transform_xml_response(root)

            

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
        
	# Embed the 'body_html' into the XML template		
        xml_output = xml_template.format(headline,headline_extended,body_html,slugline)
        xml_output = clean_html_content(xml_output)
            
        return xml_output
		


def extract_manual_tags(data):
    manual_tags = []

    if "tags" in data:
        # Loop through each tag type (like 'subject', 'person', etc.)
        for category, tags in data['tags'].items():
            # Loop through each tag in the tag type
            
            for tag in tags:
                # Check if the source is 'manual'
                if tag.get("source") == "manual":
                    manual_tags.append(tag)

    return manual_tags

def init_app(app):
    
    a = Semaphore(app)
    return a.output
