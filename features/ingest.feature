Feature: Fetch From Ingest

    @auth
    Scenario: List empty ingest
        Given empty "ingest"
        When we get "/ingest"
        Then we get list with 0 items


    @auth
    Scenario: Ingested articles get default priority and urgency
        Given "ingest"
            """
            [{
                "guid": "tag_example.com_0000_newsml_BRE9A605",
                "source": "example.com",
                "versioncreated": "2013-11-11T11:11:11+00:00"
            }]
            """

        When we get "/ingest"
        Then we get existing resource
        """
        {
            "_items": [
                {
                    "_id": "tag_example.com_0000_newsml_BRE9A605",
                    "urgency": 3,
                    "priority": 6
                }
            ]
        }
        """


    @auth
    Scenario: List ingest with items for aggregates
        Given "ingest"
            """
            [{
                "guid": "tag_example.com_0000_newsml_BRE9A605",
                "urgency": "1",
                "source": "example.com",
                "versioncreated": "2013-11-11T11:11:11+00:00"
            }]
            """

        When we get "/ingest"
        Then we get list with 1 items
        And we get aggregations "type,desk,urgency,category,source,priority,genre,sms,legal"


    @auth
    @provider
    Scenario: Fetch an ingest package
    	Given empty "ingest"
    	When we fetch from "reuters" ingest "tag_reuters.com_2014_newsml_KBN0FL0NM:10"
        And we get "/ingest"
        Then we get existing resource
		"""
		{
            "_items": [
                {
                    "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F0MS:2",
                    "ingest_provider_sequence": "3",
                    "state": "ingested",
                    "type": "picture"
                },
                {
                    "groups": [
                        {
                            "refs": [
                                {"itemClass": "icls:text", "guid": "tag_reuters.com_2014_newsml_KBN0FL0NN:5"},
                                {"itemClass": "icls:picture", "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F13M:1"},
                                {"itemClass": "icls:picture", "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F0MS:2"},
                                {"itemClass": "icls:picture", "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F0MT:2"}
                            ]
                        },
                        {"refs": [{"itemClass": "icls:text", "guid": "tag_reuters.com_2014_newsml_KBN0FL0ZP:2"}]}
                    ],
                    "guid": "tag_reuters.com_2014_newsml_KBN0FL0NM:10",
                    "ingest_provider_sequence": "6",
                    "state": "ingested",
                    "type": "composite",
                    "usageterms": "NO ARCHIVAL USE"
                },
                {
                    "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F0MT:2",
                    "ingest_provider_sequence": "2",
                    "state": "ingested",
                    "type": "picture"
                },
                {
                    "guid": "tag_reuters.com_2014_newsml_KBN0FL0ZP:2",
                    "ingest_provider_sequence": "1",
                    "state": "ingested",
                    "type": "text",
                    "word_count" : 780,
                    "priority": 4,
                    "urgency": 4
                },
                {
                    "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F13M:1",
                    "ingest_provider_sequence": "4",
                    "state": "ingested",
                    "type": "picture"
                },
                {
                    "guid": "tag_reuters.com_2014_newsml_KBN0FL0NN:5",
                    "ingest_provider_sequence": "5",
                    "state": "ingested",
                    "type": "text"
                }
            ]
        }
  		"""

    @auth
    @provider
    Scenario: Check if Ingest Provider Sequence Number is per channel
    	Given empty "ingest"
    	When we fetch from "reuters" ingest "tag_reuters.com_2014_newsml_LYNXMPEA6F0MS:2"
        And we fetch from "AAP" ingest "aap.xml"
        And we get "/ingest/#reuters.tag_reuters.com_2014_newsml_LYNXMPEA6F0MS:2#"
        Then we get existing resource
		"""
		{
          "type": "picture",
          "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F0MS:2",
          "state":"ingested",
          "ingest_provider_sequence" : "1"
		}
  		"""
        When we get "/ingest/#AAP.AAP.115314987.5417374#"
        Then we get existing resource
		"""
		{
          "type": "text",
          "guid": "AAP.115314987.5417374",
          "state":"ingested",
          "ingest_provider_sequence" : "1747"
		}
  		"""

    @auth
    @provider
    Scenario: Test iptc code expansion
        Given empty "ingest"
        When we fetch from "AAP" ingest "aap-1.xml"
        And we get "/ingest"
        Then we get existing resource
		"""
		{
                    "_items": [
                        {
                            "type": "text",
                            "subject": [
                                {
                                    "name": "Formula One",
                                    "qcode": "15039001"
                                },
                                {
                                    "name": "sport",
                                    "qcode": "15000000"
                                },
                                {
                                    "name": "motor racing",
                                    "qcode": "15039000"
                                }
                            ]
                        }
                    ]
                }
  		"""

    @auth
    @provider
    Scenario: Deleting an Ingest Provider after receiving items should be prohibited
    	Given empty "ingest"
    	When we fetch from "AAP" ingest "aap.xml"
        And we get "/ingest/#AAP.AAP.115314987.5417374#"
        Then we get "ingest_provider"
        When we delete "/ingest_providers/#ingest_provider#"
        Then we get error 403
        """
        {"_message": "Deleting an Ingest Source after receiving items is prohibited."}
        """

    @auth
    @notification
    Scenario: Ingested item must have unique id and unique name
        Given empty "archive"
        And "desks"
        """
        [{"name": "Sports"}]
        """
        Given "ingest"
            """
            [{
                "guid": "tag_example.com_0000_newsml_BRE9A605",
                "urgency": "1",
                "source": "example.com",
                "versioncreated": "2013-11-11T11:11:11+00:00"
            }, {
                "guid": "tag_example.com_0000_newsml_BRE9A606",
                "urgency": "1",
                "source": "example.com",
                "versioncreated": "2013-11-11T11:11:11+00:00"
            }]
            """
        Then we get "unique_id" in "/ingest/tag_example.com_0000_newsml_BRE9A605"
        And we get "unique_name" in "/ingest/tag_example.com_0000_newsml_BRE9A605"
        When we get "/ingest"
        Then we get existing resource
        """
        {
            "_items": [
                {
                    "_id": "tag_example.com_0000_newsml_BRE9A605",
                    "unique_id": 1
                },
                {
                    "_id": "tag_example.com_0000_newsml_BRE9A606",
                    "unique_id": 2
                }
            ]
        }
        """

        When we post to "/ingest/tag_example.com_0000_newsml_BRE9A606/fetch"
        """
        {"desk": "#desks._id#"}
        """
        Then we get new resource
        And we get notifications
        """
        [
            {
                "event": "item:fetch",
                "extra": {
                    "item": "tag_example.com_0000_newsml_BRE9A606",
                    "to_desk": "#desks._id#",
                    "to_stage": "#desks.incoming_stage#"
                }
            }
        ]
        """
        When we get "/archive?q=#desks._id#"
        Then we get list with 1 items
        """
        {"_items": [
          {
              "ingest_id": "tag_example.com_0000_newsml_BRE9A606",
              "unique_id": 1
          }
        ]}
        """


    @auth
    @provider
    Scenario: Check if Ingest from AAP populates all subjects with qcode
    	Given empty "ingest"
        When we fetch from "AAP" ingest "aap.xml"
        And we get "/ingest"
        Then we get existing resource
		"""
		{
		"_items": [
		  {
		    "type": "text",
		    "subject" : [
              {
                  "name" : "Justice",
                  "qcode" : "02000000"
              },
              {
                  "name" : "Police",
                  "qcode" : "02003000"
              }
              ]
		  }
		  ]
		}
  		"""

    @auth
    @provider
    Scenario: Check if Ingest of IPTC sample NITF populates all subjects with qcode
    	Given empty "ingest"
        When we fetch from "AAP" ingest "nitf-fishing.xml"
        And we get "/ingest"
        Then we get existing resource
		"""
		{
		"_items": [
		  {
		    "type": "text",
		    "subject" : [
              {
                  "name" : "Weather",
                  "qcode" : "17000000"
              },
              {
                  "name" : "Statistics",
                  "qcode" : "17004000"
              },
              {
                  "name" : "Fishing Industry",
                  "qcode" : "04001002"
              }
              ]
		  }
		  ]
		}
  		"""

    @auth
    @provider
    Scenario: Check if Ingest of IPTC sample NITF populates anpa category based on mapping
        Given empty "ingest"
        Given the "vocabularies"
        """
          [{
              "_id": "iptc_category_map",
              "items": [
                {"name" : "Finance", "category" : "f", "qcode" : "04000000", "is_active" : true},
                {"name" : "Weather", "category" : "b", "qcode" : "17000000", "is_active" : true}
              ]
           },
           {
              "_id": "categories",
              "items": [
                {"is_active": true, "name": "Australian Weather", "qcode": "b", "subject": "17000000"},
                {"is_active": true, "name": "Finance", "qcode": "f", "subject": "04000000"}
              ]
           }
          ]
        """
        When we fetch from "AAP" ingest "nitf-fishing.xml"
        And we get "/ingest"
        Then we get existing resource
		"""
		{
		"_items": [
		  {
		    "type": "text",
		    "anpa_category" : [
              {
                  "name" : "Australian Weather",
                  "qcode" : "b"
              },
              {
                  "name" : "Finance",
                  "qcode" : "f"
              }
              ]
		  }
		  ]
		}
  		"""

    @auth
    @provider
    Scenario: Check given an item with an anpa category the iptc subject is derived
    	Given empty "ingest"
        Given the "vocabularies"
        """
          [
           {
              "_id": "categories",
              "items": [
                {"is_active": true, "name": "Overseas Sport", "qcode": "s", "subject": "15000000"}
              ]
           }
          ]
        """
        When we fetch from "DPA" ingest "IPTC7901_odd_charset.txt"
        And we get "/ingest"
        Then we get existing resource
		"""
		{
		"_items": [
		  {
		    "subject" : [
              {
                  "name" : "sport",
                  "qcode" : "15000000"
              }
              ]
		  }
		  ]
		}
  		"""

    @auth
    @provider
    Scenario: Delete an ingest package
        Given empty "ingest"
        When we fetch from "reuters" ingest "tag_reuters.com_2014_newsml_KBN0FL0NM:10"
        And we get "/ingest"
        Then we get existing resource
        """
        {
            "_items": [
                {
                    "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F0MS:2",
                    "ingest_provider_sequence": "3",
                    "state": "ingested",
                    "type": "picture"
                },
                {
                    "groups": [
                        {
                            "refs": [
                                {"itemClass": "icls:text", "guid": "tag_reuters.com_2014_newsml_KBN0FL0NN:5"},
                                {"itemClass": "icls:picture", "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F13M:1"},
                                {"itemClass": "icls:picture", "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F0MS:2"},
                                {"itemClass": "icls:picture", "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F0MT:2"}
                            ]
                        },
                        {"refs": [{"itemClass": "icls:text", "guid": "tag_reuters.com_2014_newsml_KBN0FL0ZP:2"}]}
                    ],
                    "guid": "tag_reuters.com_2014_newsml_KBN0FL0NM:10",
                    "ingest_provider_sequence": "6",
                    "state": "ingested",
                    "type": "composite",
                    "usageterms": "NO ARCHIVAL USE"
                },
                {
                    "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F0MT:2",
                    "ingest_provider_sequence": "2",
                    "state": "ingested",
                    "type": "picture"
                },
                {
                    "guid": "tag_reuters.com_2014_newsml_KBN0FL0ZP:2",
                    "ingest_provider_sequence": "1",
                    "state": "ingested",
                    "type": "text"
                },
                {
                    "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F13M:1",
                    "ingest_provider_sequence": "4",
                    "state": "ingested",
                    "type": "picture"
                },
                {
                    "guid": "tag_reuters.com_2014_newsml_KBN0FL0NN:5",
                    "ingest_provider_sequence": "5",
                    "state": "ingested",
                    "type": "text"
                }
            ]
        }
        """

        When we find for "ingest" the id as "ingest_packet" by "source={"filter":{"term":{"guid": "tag_reuters.com_2014_newsml_KBN0FL0NM:10"}}}"

        When we delete "/ingest/#ingest_packet#"
        Then we get response code 204

        When we get "/ingest"
        Then we get list with 0 items

    @auth
    @provider
    Scenario: Ingest ninjs
        Given empty "ingest"
        When we fetch from "ninjs" ingest "ninjs5.json"
        And we get "/ingest"
        Then we get existing resource
        """
        {
           "_items":[
              {
                 "type":"picture",
                 "state":"ingested",
                 "renditions":{
                    "baseImage":{
                       "width":1400
                    },
                    "thumbnail":{

                    },
                    "original":{

                    },
                    "viewImage":{
                    }
                 }
              },
              {
                 "type":"text",
                 "state":"ingested",
                 "associations":{
                    "featuremedia":{
                       "state": "ingested",
                       "renditions":{
                          "baseImage":{
                             "width":1400
                          },
                          "original":{
                          }
                       }
                    }
                 }
              }
           ]
        }
        """

    @auth
    @provider
    Scenario: Ingest ninjs with embedded items
        Given empty "ingest"
        When we fetch from "ninjs" ingest "ninjs4.json" (mocking with "ninjs4_mock.json")
        And we get "/ingest"
        Then we get existing resource
        """
        {
           "_items":[
              {
                 "type":"picture",
                 "state":"ingested",
                 "headline": "Polizeihunde sollen effizienter trainiert werden – Klone sollen die Lösung sein.",
                 "renditions":{
                    "baseImage":{
                       "width":1400
                    },
                    "thumbnail":{

                    },
                    "original":{

                    },
                    "viewImage":{
                    }
                 }
              },
              {
                 "type":"picture",
                 "state":"ingested",
                 "headline": "Ob China bald ganze Polizeihund-Staffeln voller Klone haben wird?"
              },
              {
                 "type":"text",
                 "state":"ingested",
                 "associations":{
                    "featuremedia":{
                       "state": "ingested",
                       "renditions":{
                          "baseImage":{
                             "width":1400
                          },
                          "original":{
                          }
                       }
                    }
                 }
              }
           ]
        }
        """

    @auth
    @provider
    Scenario: Ingest ninjs text
        Given empty "ingest"
        When we fetch from "ninjs" ingest "ninjs1.json"
        And we get "/ingest"
        Then we get existing resource
        """
        {
           "_items":[{"type": "text", "headline": "headline"}]
        }
        """

    @auth
    @provider
    Scenario: Ingest ninjs picture
        Given empty "ingest"
        When we fetch from "ninjs" ingest "ninjs6.json"
        And we get "/ingest"
        Then we get existing resource
        """
        {
           "_items":[
              {
                 "type":"picture",
                 "headline":"German Air Force Museum",
                 "state":"ingested",
                 "renditions":{
                    "baseImage" : {
                       "width" : 1400,
                       "height" : 1074,
                       "mimetype" : "image/jpeg"
                    },
                    "thumbnail" : {
                        "width":156,
                        "height":120,
                        "mimetype" : "image/jpeg"
                    },
                    "original" : {
                       "width" : 800,
                       "height" : 614,
                       "mimetype" : "image/jpeg"
                    },
                    "viewImage":{
                        "width" : 640,
                        "height" : 491,
                        "mimetype" : "image/jpeg"
                    }
                 }
              }
           ]
        }
        """
