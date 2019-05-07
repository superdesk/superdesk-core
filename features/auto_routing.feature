Feature: Auto Routing

    @auth @provider @vocabulary
    Scenario: Content is fetched based on subject metadata
        Given empty "desks"
        Given "filter_conditions"
        """
        [{
            "_id": "1111111111aaaa1111111111",
            "name": "Finance Content",
            "field": "subject",
            "operator": "in",
            "value": "04000000"
        },
        {
            "_id": "2222222222bbbb2222222222",
            "name": "Sports Content",
            "field": "subject",
            "operator": "in",
            "value": "15000000"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "0987654321dcba0987654321",
            "name": "Finance Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["1111111111aaaa1111111111"]
                    }
                }
            ]
        },
        {
            "_id": "1234567890abcd1234567890",
            "name": "Sports Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["2222222222bbbb2222222222"]
                    }
                }
            ]
        }]
        """
        When we post to "/desks"
        """
          {
            "name": "Sports Desk", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Sports Rule",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "fetch": [
                    {
                      "desk": "#desks._id#",
                      "stage": "#desks.incoming_stage#"
                    }],
                  "exit": false
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we post to "/desks"
        """
          {
            "name": "Finance Desk", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        When we patch routing scheme "/routing_schemes/#routing_schemes._id#"
        """
           {
              "name": "Finance Rule",
              "filter": "0987654321dcba0987654321",
              "actions": {
                "fetch": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}],
                "exit": false
              }
           }
        """
        Then we get response code 200
        When we fetch from "AAP" ingest "aap-finance.xml" using routing_scheme
        """
        #routing_schemes._id#
        """
        Then the ingest item is routed based on routing scheme and rule "Finance Rule"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#AAP.AFP.121974877.6504909#"
        }
        """
        Then the ingest item is not routed based on routing scheme and rule "Sports Rule"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#AAP.AFP.121974877.6504909#"
        }
        """
        When we fetch from "AAP" ingest "aap-sports.xml" using routing_scheme
        """
        #routing_schemes._id#
        """
        Then the ingest item is routed based on routing scheme and rule "Sports Rule"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#AAP.AAP.123253116.6697929#"
        }
        """
        When we get "/archive_history"
        Then we get list with 2 items
        """
        {"_items": [
          {"version": 1, "operation": "fetch", "user_id": "__none__"},
          {"version": 1, "operation": "fetch", "user_id": "__none__"}
        ]}
        """
        Then the ingest item is not routed based on routing scheme and rule "Finance Rule"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#AAP.AAP.123253116.6697929#"
        }
        """

    @auth @provider @vocabulary
    Scenario: Package is routed automatically
        Given empty "desks"
        Given "filter_conditions"
        """
        [{
            "_id": "1111111111aaaa1111111111",
            "name": "Syria in Slugline",
            "field": "slugline",
            "operator": "like",
            "value": "syria"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "1234567890abcd1234567890",
            "name": "Syria Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["1111111111aaaa1111111111"]
                    }
                }
            ]
        }]
        """
        When we post to "/desks"
        """
          {
            "name": "World Desk", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Syria Rule",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "fetch": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}],
                  "exit": false
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we fetch from "reuters" ingest "tag_reuters.com_2014_newsml_KBN0FL0NM:10" using routing_scheme
        """
        #routing_schemes._id#
        """
        Then the ingest item is routed based on routing scheme and rule "Syria Rule"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#reuters.tag_reuters.com_2014_newsml_KBN0FL0NM:10#"
        }
        """

    @auth @provider @vocabulary
    Scenario: Content is fetched and published to different stages 1
        Given the "validators"
        """
          [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
        """
        Given empty "desks"
        Given "filter_conditions"
        """
        [{
            "_id": "2222222222bbbb2222222222",
            "name": "Finance Subject",
            "field": "subject",
            "operator": "in",
            "value": "04000000"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "1234567890abcd1234567890",
            "name": "Finance Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["2222222222bbbb2222222222"]
                    }
                }
            ]
        }]
        """

        When we post to "/desks"
        """
          {
            "name": "Finance Desk", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Finance Rule 1",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "fetch": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}],
                  "exit": false
                }
              }
            ]
          }
        ]
        """
        Then we get OK response
        When we post to "/stages"
        """
        [
          {
            "name": "Published",
            "description": "Published Content",
            "task_status": "in_progress",
            "desk": "#desks._id#"
          }
        ]
        """
        Then we get "_id"
        When we post to "/stages"
        """
        [
          {
            "name": "Un Publsihed",
            "description": "Published Content",
            "task_status": "in_progress",
            "desk": "#desks._id#"
          }
        ]
        """
        Then we get OK response
        When we fetch from "AAP" ingest "aap-finance.xml" using routing_scheme
        """
        #routing_schemes._id#
        """
        Then the ingest item is routed based on routing scheme and rule "Finance Rule 1"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#AAP.AFP.121974877.6504909#"
        }
        """
        Then the ingest item is routed based on routing scheme and rule "Finance Rule 2"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#AAP.AFP.121974877.6504909#"
        }
        """
        When we fetch from "AAP" ingest "aap-finance1.xml" using routing_scheme
        """
        #routing_schemes._id#
        """
        Then the ingest item is routed based on routing scheme and rule "Finance Rule 2"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#AAP.AAP.0.6703189#"
        }
        """
        Then the ingest item is routed based on routing scheme and rule "Finance Rule 1"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#AAP.AAP.0.6703189#"
        }
        """


    @auth @provider @vocabulary
    Scenario: Content is fetched and published to different stages 2
        Given empty "desks"
        Given "filter_conditions"
        """
        [{
            "_id": "2222222222bbbb2222222222",
            "name": "Finance Subject",
            "field": "subject",
            "operator": "in",
            "value": "04000000"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "1234567890abcd1234567890",
            "name": "Finance Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["2222222222bbbb2222222222"]
                    }
                }
            ]
        }]
        """

        When we post to "/desks"
        """
          {
            "name": "Finance Desk", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Finance Rule 1",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "fetch": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}],
                  "exit": false
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we post to "/stages"
        """
        [
          {
            "name": "Published",
            "description": "Published Content",
            "task_status": "in_progress",
            "desk": "#desks._id#"
          }
        ]
        """
        When we patch routing scheme "/routing_schemes/#routing_schemes._id#"
        """
           {
              "name": "Finance Rule 2",
              "filter": "1234567890abcd1234567890",
              "actions": {
                "fetch": [{"desk": "#desks._id#", "stage": "#stages._id#"}],
                "exit": false
              }
           }
        """
        Then we get response code 200
        When we schedule the routing scheme "#routing_schemes._id#"
        When we fetch from "AAP" ingest "aap-finance.xml" using routing_scheme
        """
        #routing_schemes._id#
        """
        Then the ingest item is not routed based on routing scheme and rule "Finance Rule 1"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#AAP.AFP.121974877.6504909#"
        }
        """
        Then the ingest item is routed based on routing scheme and rule "Finance Rule 2"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#AAP.AFP.121974877.6504909#"
        }
        """


    @auth @provider @vocabulary
    Scenario: Content is fetched to desk in the ingested item
        Given empty "desks"
        Given "filter_conditions"
        """
        [{
            "_id": "2222222222bbbb2222222222",
            "name": "Finance Subject",
            "field": "subject",
            "operator": "in",
            "value": "04000000"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "1234567890abcd1234567890",
            "name": "Finance Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["2222222222bbbb2222222222"]
                    }
                }
            ]
        }]
        """

        When we post to "/desks"
        """
          {
            "name": "Finance Desk", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Finance Rule 1",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "fetch": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}],
                  "preserve_desk": true,
                  "exit": false
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we ingest and fetch "AAP" "aap-finance.xml" to desk "#desks._id#" stage "#desks.incoming_stage#" using routing_scheme
        """
        #routing_schemes._id#
        """
        When we get "/archive?q=#desks._id#"
        Then we get list with 1 items
        """
        {"_items": [
          {
              "headline": "ASIA:Samsung sells defence, petrochemical units"
          }
        ]}
        """

    @auth @provider @vocabulary
    Scenario: Content is fetched to desk and stage contained in the ingested item
        Given empty "desks"
        Given "filter_conditions"
        """
        [{
            "_id": "2222222222bbbb2222222222",
            "name": "Finance Subject",
            "field": "subject",
            "operator": "in",
            "value": "04000000"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "1234567890abcd1234567890",
            "name": "Finance Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["2222222222bbbb2222222222"]
                    }
                }
            ]
        }]
        """

        When we post to "/desks"
        """
          {
            "name": "Finance Desk", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        When we post to "/stages"
        """
        {"name": "None default stage", "description": "A stage that is not default incomming", "desk": "#desks._id#"}
        """
        Then we get OK response
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Finance Rule 1",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "preserve_desk": true,
                  "exit": false
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we ingest with routing scheme "AAP" "aap-cyber.xml"
        """
        #routing_schemes._id#
        """
        When we get "/archive?q=#desks._id#"
        Then we get list with 1 items
        """
        {"_items": [
          {
              "headline": "Headline",
              "task": {"stage": "#stages._id#"}
          }
        ]}
        """

    @auth @provider @clean @vocabulary
    Scenario: Content is fetched and transformed different stages
        Given empty "desks"
        Given "filter_conditions"
        """
        [{
            "_id": "3333333333cccc3333333333",
            "name": "Politics Subject",
            "field": "subject",
            "operator": "in",
            "value": "04000000"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "1234567890abcd1234567890",
            "name": "Politics Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["3333333333cccc3333333333"]
                    }
                }
            ]
        }]
        """

        When we post to "/desks"
        """
          {
            "name": "Politics", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        Given we create a new macro "behave_macro.py"
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Politics Rule 1",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "fetch": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "macro": "update_fields"}],
                  "exit": false
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we post to "/stages"
        """
        [
          {
            "name": "Published",
            "description": "Published Content",
            "task_status": "in_progress",
            "desk": "#desks._id#"
          }
        ]
        """
        When we patch routing scheme "/routing_schemes/#routing_schemes._id#"
        """
           {
              "name": "Politics Rule 2",
              "filter": "1234567890abcd1234567890",
              "actions": {
                "fetch": [{"desk": "#desks._id#", "stage": "#stages._id#", "macro": "update_fields"}],
                "exit": false
              }
           }
        """
        Then we get response code 200
        When we schedule the routing scheme "#routing_schemes._id#"
        When we fetch from "AAP" ingest "aap-finance.xml" using routing_scheme
        """
        #routing_schemes._id#
        """
        Then the ingest item is not routed based on routing scheme and rule "Politics Rule 1"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#AAP.AFP.121974877.6504909#"
        }
        """
        Then the ingest item is routed and transformed based on routing scheme and rule "Politics Rule 2"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#AAP.AFP.121974877.6504909#"
        }
        """

    @auth @provider @vocabulary
    Scenario: a versioned item with the same version ingested twice gets routed once
        Given empty "desks"
        Given "filter_conditions"
        """
        [{
            "_id": "1111111111aaaa1111111111",
            "name": "Syria in Slugline",
            "field": "slugline",
            "operator": "like",
            "value": "syria"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "1234567890abcd1234567890",
            "name": "Syria Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["1111111111aaaa1111111111"]
                    }
                }
            ]
        }]
        """
        When we post to "/desks"
        """
          {
            "name": "World Desk", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Syria Rule",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "fetch": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}],
                  "exit": false
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we fetch from "reuters" ingest "tag_reuters.com_2014_newsml_KBN0FL0NN:5" using routing_scheme
        """
        #routing_schemes._id#
        """
        When we fetch from "reuters" ingest "tag_reuters.com_2014_newsml_KBN0FL0NN:5" using routing_scheme
        """
        #routing_schemes._id#
        """
        Then the ingest item is routed based on routing scheme and rule "Syria Rule"
        """
        {
          "routing_scheme": "#routing_schemes._id#",
          "ingest": "#reuters.tag_reuters.com_2014_newsml_KBN0FL0NN:5#"
        }
        """
        When we get "/archive"
        Then we get list with 1 items

    @auth @provider @vocabulary
    Scenario: Content is ingested and auto published
        Given empty "desks"
        Given the "validators"
        """
          [{"_id": "publish_text", "act": "auto_publish", "type": "text", "schema":{}}]
        """
        Given "filter_conditions"
        """
        [{
            "_id": "2222222222bbbb2222222222",
            "name": "Finance Subject",
            "field": "subject",
            "operator": "in",
            "value": "04000000"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "1234567890abcd1234567890",
            "name": "Finance Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["2222222222bbbb2222222222"]
                    }
                }
            ]
        }]
        """
        When we post to "/desks"
        """
          {
            "name": "Finance Desk", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Finance Rule 1",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "fetch": [],
                  "publish": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}],
                  "exit": true
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we ingest with routing scheme "AAP" "aap-finance.xml"
        """
        #routing_schemes._id#
        """
        When we get "/published"
        Then we get list with 1 items
        """
        {"_items": [
          {
              "headline": "ASIA:Samsung sells defence, petrochemical units", "type": "text"
          }
        ]}
        """

    @auth @provider @vocabulary
    Scenario: Content is ingested and auto published with default values
        Given empty "desks"
        Given the "validators"
        """
          [{"_id": "publish_text", "act": "auto_publish", "type": "text", "schema":{}}]
        """
        Given "filter_conditions"
        """
        [{
            "_id": "2222222222bbbb2222222222",
            "name": "Finance Subject",
            "field": "subject",
            "operator": "in",
            "value": "04000000"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "1234567890abcd1234567890",
            "name": "Finance Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["2222222222bbbb2222222222"]
                    }
                }
            ]
        }]
        """
        When we post to "/desks"
        """
          {
            "name": "Finance Desk", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Finance Rule 1",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "fetch": [],
                  "publish": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}],
                  "exit": true
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we ingest with routing scheme "AAP" "aap-finance-lite.xml"
        """
        #routing_schemes._id#
        """
        When we get "/published"
        Then we get list with 1 items
        """
        {"_items": [
          {
              "headline": " ",
              "body_html": "<p></p>",
              "type": "text",
              "anpa_category":  [{"name": "Australian General News", "qcode": "a"}]
          }
        ]}
        """

        @auth @provider @vocabulary
        Scenario: Content is ingested and auto published to targeted subscribers
        Given empty "desks"
        Given the "validators"
        """
          [{"_id": "publish_text", "act": "auto_publish", "type": "text", "schema":{}}]
        """
        Given "filter_conditions"
        """
        [{
            "_id": "2222222222bbbb2222222222",
            "name": "Finance Subject",
            "field": "subject",
            "operator": "in",
            "value": "04000000"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "1234567890abcd1234567890",
            "name": "Finance Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["2222222222bbbb2222222222"]
                    }
                }
            ]
        }]
        """
        Given "subscribers"
        """
        [{
          "_id": "sub-1",
          "name":"Channel 1",
          "media_type": "media",
          "subscriber_type": "digital",
          "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "codes": "Aaa",
          "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
        },
        {
          "_id": "sub-2",
          "name":"Wire channel with geo restriction Victoria",
          "media_type":"media",
          "subscriber_type": "wire",
          "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
        },
        {
          "_id": "sub-3",
          "name":"Wire channel without geo restriction",
          "media_type":"media",
          "subscriber_type": "wire",
          "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
        }]
        """
        When we post to "/desks"
        """
          {
            "name": "Finance Desk", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Finance Rule 1",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "fetch": [],
                  "publish": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "target_subscribers": [{"_id":"sub-2"}]}],
                  "exit": true
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we ingest with routing scheme "AAP" "aap-finance.xml"
        """
        #routing_schemes._id#
        """
        When we get "/published"
        Then we get list with 1 items
        """
        {"_items": [
          {
              "headline": "ASIA:Samsung sells defence, petrochemical units", "type": "text",
              "auto_publish": true
          }
        ]}
        """
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 1 items
        """
        {
          "_items":
            [
              {"subscriber_id": "sub-2"}
            ]
        }
        """

    @auth @provider @vocabulary
    Scenario: Content is ingested and auto published not using content profile
        Given config update
        """
        {"AUTO_PUBLISH_CONTENT_PROFILE": false}
        """
        Given empty "desks"
        Given the "validators"
        """
          [{"_id": "publish_text", "act": "auto_publish", "type": "text", "schema":{}}]
        """
        Given "filter_conditions"
        """
        [{
            "_id": "2222222222bbbb2222222222",
            "name": "Finance Subject",
            "field": "subject",
            "operator": "in",
            "value": "04000000"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "1234567890abcd1234567890",
            "name": "Finance Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["2222222222bbbb2222222222"]
                    }
                }
            ]
        }]
        """
        When we post to "content_types"
        """
        [{
            "_id": "foo",
            "schema" : {
                "body_html" : {
                    "required" : true,
                    "type" : "string"
                },
                "headline" : {
                    "required" : true,
                    "maxlength" : 30,
                    "type" : "string"
                },
                "body_footer" : {
                    "type" : "string",
                    "default" : "test",
                    "maxlength": null
                },
                "slugline" : {
                    "required" : true,
                    "maxlength" : 24,
                    "type" : "string"
                }
            }
        }]
        """
        Then we get response code 201
        When we post to "/desks"
        """
          {
            "name": "Finance Desk",
            "members": [{"user": "#CONTEXT_USER_ID#"}],
            "default_content_profile": "#content_types._id#"
          }
        """
        Then we get response code 201
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Finance Rule 1",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "fetch": [],
                  "publish": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}],
                  "exit": true
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we ingest with routing scheme "AAP" "aap-finance.xml"
        """
        #routing_schemes._id#
        """
        When we get "/published"
        Then we get list with 1 items
        """
        {"_items": [
          {
              "headline": "ASIA:Samsung sells defence, petrochemical units",
              "type": "text",
              "profile": "#content_types._id#"
          }
        ]}
        """
        When we find for "published" the id as "published_doc" by "where={"type": "text"}"
        Then we get OK response
        When we post to "/archive/#published_doc#/duplicate"
        """
        {"desk": "#desks._id#","type": "archive"}
        """
        Then we get OK response
        When we publish "#duplicate._id#" with "publish" type and "published" state
        Then we get error 400
        """
         {"_issues": {"validator exception": "[['HEADLINE is too long']]"}, "_status": "ERR"}
        """

    @auth @provider @vocabulary
    Scenario: Content is fetched and published using desk profile
        Given config update
        """
        {"AUTO_PUBLISH_CONTENT_PROFILE": true}
        """
        Given "validators"
        """
        [
          {
            "_id": "auto_publish_text",
            "act": "auto_publish",
            "type": "text",
            "schema": {
                "headline": {
                    "type": "string",
                    "required": true,
                    "nullable": false,
                    "empty": false,
                    "minlength": 10,
                    "maxlength": 42
                }
            }
          }
        ]
        """
        Given "content_types"
        """
        [
          {"_id": "story", "schema": {"headline": {}, "body_html": {}}}
        ]
        """
        When we post to "/desks"
        """
          {
            "name": "Finance Desk", "members": [{"user": "#CONTEXT_USER_ID#"}],
            "default_content_profile": "story"
          }
        """
        Then we get response code 201
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "publish",
            "rules": [
              {
                "name": "publish",
                "actions": {
                  "publish": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}],
                  "exit": false
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we fetch from "AAP" ingest "aap-finance-lite.xml" using routing_scheme
        """
        #routing_schemes._id#
        """
        And we get "/published"
        Then we get list with 1 items
        """
        {
          "_items": [{
            "profile": "story"
          }]
        }
        """



    @auth @provider @vocabulary
    Scenario: Content is ingested and auto published
        Given empty "desks"
        Given the "validators"
        """
          [{"_id": "publish_text", "act": "auto_publish", "type": "text", "schema":{}}]
        """
        Given "filter_conditions"
        """
        [{
            "_id": "123",
            "name": "Headline Test",
            "field": "headline",
            "operator": "like",
            "value": "Mikko"
        }]
        """
        Given "content_filters"
        """
        [{
            "_id": "1234567890abcd1234567890",
            "name": "Headline Content",
            "content_filter": [
                {
                    "expression": {
                        "fc": ["123"]
                    }
                }
            ]
        }]
        """
        Given "subscribers"
        """
        [{
          "_id": "sub-1",
          "name":"Channel 1",
          "media_type": "media",
          "subscriber_type": "digital",
          "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "codes": "Aaa",
          "destinations":[{"name":"Test","format": "newsroom ninjs", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
        }]
        """
        When we post to "/desks"
        """
          {
            "name": "Finance Desk", "members": [{"user": "#CONTEXT_USER_ID#"}]
          }
        """
        Then we get response code 201
        When we post to "/routing_schemes"
        """
        [
          {
            "name": "routing rule scheme 1",
            "rules": [
              {
                "name": "Finance Rule 1",
                "filter": "1234567890abcd1234567890",
                "actions": {
                  "fetch": [],
                  "publish": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "target_subscribers": [{"_id":"sub-1"}]}],
                  "exit": true
                }
              }
            ]
          }
        ]
        """
        Then we get response code 201
        When we ingest with routing scheme "STT" "stt1.xml"
        """
        #routing_schemes._id#
        """
        When we get "/published"
        Then we get list with 1 items
        """
        {"_items": [
          {
              "headline": "Mikko Moilanen siirtyy Revenion toimitusjohtajaksi",
              "type": "text",
              "auto_publish": true,
              "ingest_id": "urn:newsml:stt.fi::102736761",
              "ingest_version": "2"
          }
        ]}
        """
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 1 items
        """
        {
          "_items":
            [
              {"subscriber_id": "sub-1"}
            ]
        }
        """
