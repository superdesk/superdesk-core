Feature: Rewrite content

    @auth
    Scenario: Rewrite a published content
      Given the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "body_html": "Test Document body", "genre": [{"name": "Article", "qcode": "Article"}],
        "flags": {"marked_for_legal": true, "marked_for_sms": true}, "priority": 2, "urgency": 2,
        "body_footer": "Suicide Call Back Service 1300 659 467", "sms_message": "test",
        "place": [{"qcode" : "ACT", "world_region" : "Oceania", "country" : "Australia",
        "name" : "ACT", "state" : "Australian Capital Territory"}],
        "company_codes" : [{"qcode" : "1PG", "security_exchange" : "ASX", "name" : "1-PAGE LIMITED"}]
      }]
      """
      When we post to "/stages"
      """
      [
        {
        "name": "another stage",
        "description": "another stage",
        "task_status": "in_progress",
        "desk": "#desks._id#"
        }
      ]
      """
      And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#stages._id#"}}]
        """
      Then we get OK response
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media",
        "subscriber_type": "digital",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we patch "archive/123"
      """
      {"target_subscribers": [{"_id": "#subscribers._id#"}]}
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 4, "state": "published", "task":{"desk": "#desks._id#", "stage": "#stages._id#"}}
      """
      When we get "/published"
      Then we get existing resource
      """
      {"_items" : [{"_id": "123", "guid": "123", "headline": "test", "_current_version": 4, "state": "published",
        "task": {"desk": "#desks._id#", "stage": "#stages._id#", "user": "#CONTEXT_USER_ID#"}}]}
      """
      When we rewrite "123"
      """
      {"desk_id": "#desks._id#"}
      """
      Then we get OK response
      When we get "/archive/#REWRITE_ID#"
      Then we get OK response
      Then we get existing resource
      """
      {"_id": "#REWRITE_ID#", "_current_version": 1, "state": "in_progress", "headline": "test"}
      """
      When we get "/published"
      Then we get existing resource
      """
      {"_items" : [{"_id": "123", "rewritten_by": "#REWRITE_ID#"}]}
      """
      When we get "/archive"
      Then we get existing resource
      """
      {"_items" : [{"_id": "#REWRITE_ID#", "anpa_take_key": "update", "rewrite_of": "123",
        "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#"}, "genre": [{"name": "Article", "qcode": "Article"}],
        "flags": {"marked_for_legal": true, "marked_for_sms": false}, "priority": 2, "urgency": 2, "rewrite_sequence": 1,
        "body_footer": "Suicide Call Back Service 1300 659 467",
        "body_html": "Test Document body",
        "company_codes" : [{"qcode" : "1PG", "security_exchange" : "ASX", "name" : "1-PAGE LIMITED"}],
        "target_subscribers": [{"_id": "#subscribers._id#"}],
        "place": [{"qcode" : "ACT"}]}]}
      """
      When we get "/archive/123"
      Then we get existing resource
      """
      {"_id": "123", "rewritten_by": "#REWRITE_ID#", "place": [{"qcode" : "ACT"}]}
      """
      When we publish "#REWRITE_ID#" with "publish" type and "published" state
      Then we get OK response
      When we rewrite "#REWRITE_ID#"
      """
      {"desk_id": "#desks._id#"}
      """
      Then we get OK response
      When we get "/archive/#REWRITE_ID#"
      Then we get OK response
      And we get existing resource
      """
      {"_id": "#REWRITE_ID#", "rewrite_of": "#REWRITE_OF#",
      "rewrite_sequence": 2, "anpa_take_key": "2nd update", "_current_version": 1}
      """

    @auth
    Scenario: Rewrite an un-published content
      Given "desks"
      """
      [{"name": "Sports"}]
      """
      And the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "body_html": "Test Document body", "genre": [{"name": "Article", "qcode": "Article"}],
        "flags": {"marked_for_legal": true},
        "body_footer": "Suicide Call Back Service 1300 659 467",
        "place": [{"qcode" : "ACT", "world_region" : "Oceania", "country" : "Australia",
        "name" : "ACT", "state" : "Australian Capital Territory"}],
        "target_subscribers": [{"_id": "abc"}],
        "company_codes" : [{"qcode" : "1PG", "security_exchange" : "ASX", "name" : "1-PAGE LIMITED"}]
      }]
      """
      When we post to "/stages"
      """
      [
        {
        "name": "another stage",
        "description": "another stage",
        "task_status": "in_progress",
        "desk": "#desks._id#"
        }
      ]
      """
      When we rewrite "123"
      """
      {"desk_id": "#desks._id#"}
      """
      When we get "/archive/#REWRITE_ID#"
      Then there is no "body_html" in response
      And we get existing resource
      """
      {
        "_id": "#REWRITE_ID#",
        "rewrite_of": "123",
        "headline": "test",
        "rewrite_sequence": 1,
        "_current_version": 1
      }
      """
      When we get "/archive/123"
      Then we get existing resource
      """
      {
        "_id": "123",
        "rewritten_by": "#REWRITE_ID#",
        "place": [{"qcode" : "ACT"}],
        "target_subscribers": [{"_id": "abc"}]
      }
      """
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we publish "#REWRITE_ID#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_id": "#REWRITE_ID#", "state": "published",
        "rewrite_sequence": 1}
      """
      When we get "/archive/#REWRITE_ID#"
      Then we get OK response
      And we get existing resource
      """
      {"state": "published", "rewrite_of": "123",
        "rewrite_sequence": 1}
      """

    @auth
      Scenario: Rewrite of a rewritten published content
        Given the "validators"
        """
          [
          {
              "schema": {},
              "type": "text",
              "act": "publish",
              "_id": "publish_text"
          },
          {
              "_id": "publish_composite",
              "act": "publish",
              "type": "composite",
              "schema": {}
          }
          ]
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body"}]
        """
        When we post to "/products" with success
        """
        {
          "name":"prod-1","codes":"abc,xyz", "product_type": "both"
        }
        """
        And we post to "/subscribers" with success
        """
        {
          "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "products": ["#products._id#"],
          "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
        }
        """
        And we publish "#archive._id#" with "publish" type and "published" state
        When we rewrite "123"
        """
        {"desk_id": "#desks._id#"}
        """
        And we patch "archive/#REWRITE_ID#"
        """
        {"abstract": "test", "body_html": "Test Document body"}
        """
        When we publish "#REWRITE_ID#" with "publish" type and "published" state
        When we get "/published"
        Then we get existing resource
        """
        {"_items" : [{"_id": "123", "rewritten_by": "#REWRITE_ID#"},
                     {"_id": "#REWRITE_ID#", "anpa_take_key": "update", "rewrite_sequence": 1}]}
        """
        When we rewrite "#REWRITE_ID#"
        """
        {"desk_id": "#desks._id#"}
        """
        When we get "/archive"
        Then we get existing resource
        """
        {"_items" : [{"_id": "#REWRITE_ID#", "anpa_take_key": "2nd update", "rewrite_sequence": 2,
          "task": {"desk": "#desks._id#"}}]}
        """

    @auth
    Scenario: Spike of an unpublished rewrite removes references
      Given the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "body_html": "Test Document body"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we get "/published"
      Then we get existing resource
      """
      {"_items" : [{"_id": "123", "guid": "123", "headline": "test", "_current_version": 2, "state": "published",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]}
      """
      When we rewrite "123"
      """
      {"desk_id": "#desks._id#"}
      """
      When we get "/published"
      Then we get existing resource
      """
      {"_items" : [{"_id": "123", "rewritten_by": "#REWRITE_ID#"}]}
      """
      When we get "/archive"
      Then we get existing resource
      """
      {"_items" : [{"_id": "#REWRITE_ID#", "anpa_take_key": "update", "rewrite_of": "123",
        "task": {"desk": "#desks._id#"}, "rewrite_sequence": 1}]}
      """
      When we spike "#REWRITE_ID#"
      Then we get OK response
      And we get spiked content "#REWRITE_ID#"
      And we get "rewrite_of" not populated
      When we get "/published"
      Then we get "rewritten_by" not populated in results
      When we get "/archive/123"
      Then we get "rewritten_by" not populated

    @auth
    Scenario: Spike of an unpublished rewrite of a rewrite removes references from last rewrite
    Given the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "body_html": "Test Document body"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      When we rewrite "123"
      """
      {"desk_id": "#desks._id#"}
      """
      And we patch "archive/#REWRITE_ID#"
      """
      {"abstract": "test", "body_html": "Test Document body"}
      """
      When we publish "#REWRITE_ID#" with "publish" type and "published" state
      When we get "/published"
      Then we get existing resource
      """
      {"_items" : [{"_id": "123", "rewritten_by": "#REWRITE_ID#"},
                   {"_id": "#REWRITE_ID#", "anpa_take_key": "update", "rewrite_sequence": 1}]}
      """
      When we rewrite "#REWRITE_ID#"
      """
      {"desk_id": "#desks._id#"}
      """
      When we get "/archive"
      Then we get existing resource
      """
      {"_items" : [{"_id": "#REWRITE_ID#", "anpa_take_key": "2nd update", "rewrite_sequence": 2,
        "task": {"desk": "#desks._id#"}}]}
      """
      When we spike "#REWRITE_ID#"
      Then we get OK response
      And we get spiked content "#REWRITE_ID#"
      And we get "rewrite_of" not populated
      When we get "/published"
      Then we get existing resource
      """
      {"_items": [{"_id": "123", "rewritten_by": "#REWRITE_OF#"}]}
      """

    @auth
    Scenario: Associate a story as update
      Given the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "body_html": "Test Document body", "genre": [{"name": "Article", "value": "Article"}],
        "flags": {"marked_for_legal": true},
        "body_footer": "Suicide Call Back Service 1300 659 467",
        "place": [{"qcode" : "ACT", "world_region" : "Oceania", "country" : "Australia",
        "name" : "ACT", "state" : "Australian Capital Territory"}],
        "company_codes" : [{"qcode" : "1PG", "security_exchange" : "ASX", "name" : "1-PAGE LIMITED"}]
      },{"guid": "456", "type": "text", "headline": "test",
        "_current_version": 1, "state": "submitted", "priority": 2,
         "subject":[{"qcode": "01000000", "name": "arts, culture and entertainment"}]}]
      """
      When we post to "/stages"
      """
      [
        {
        "name": "another stage",
        "description": "another stage",
        "task_status": "in_progress",
        "desk": "#desks._id#"
        }
      ]
      """
      And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#stages._id#"}}]
        """
      Then we get OK response
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we publish "123" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "published", "task":{"desk": "#desks._id#", "stage": "#stages._id#"}}
      """
      When we get "/published"
      Then we get existing resource
      """
      {"_items" : [{"_id": "123", "guid": "123", "headline": "test", "_current_version": 3, "state": "published",
        "task": {"desk": "#desks._id#", "stage": "#stages._id#", "user": "#CONTEXT_USER_ID#"}}]}
      """
      When we rewrite "123"
      """
      {"update": {"_id": "456", "type": "text", "headline": "test",
      "_current_version": 1, "state": "submitted", "priority": 2,
      "subject":[{"qcode": "01000000", "name": "arts, culture and entertainment"}]}}
      """
      When we get "/published"
      Then we get existing resource
      """
      {"_items" : [{"_id": "123", "rewritten_by": "456"}]}
      """
      When we get "/archive/456"
      Then we get existing resource
      """
      {"_id": "456", "anpa_take_key": "update", "priority": 2,
       "rewrite_of": "123", "rewrite_sequence": 1,
       "flags": {"marked_for_legal": true},
       "subject":[{"qcode": "17004000", "name": "Statistics"},
       {"qcode": "01000000", "name": "arts, culture and entertainment"}]}
      """
      When we get "/archive/123"
      Then we get existing resource
      """
      {"_id": "123", "rewritten_by": "456", "place": [{"qcode" : "ACT"}]}
      """

    @auth
    Scenario: Can publish rewrite after original is published
        Given the "validators"
        """
          [
          {
              "schema": {},
              "type": "text",
              "act": "publish",
              "_id": "publish_text"
          },
          {
              "_id": "publish_composite",
              "act": "publish",
              "type": "composite",
              "schema": {}
          }
          ]
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body"}]
        """
        When we post to "/products" with success
        """
        {
          "name":"prod-1","codes":"abc,xyz", "product_type": "both"
        }
        """
        And we post to "/subscribers" with success
        """
        {
          "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "products": ["#products._id#"],
          "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
        }
        """
        When we rewrite "123"
        """
        {"desk_id": "#desks._id#"}
        """
        And we patch "archive/#REWRITE_ID#"
        """
        {"abstract": "test", "body_html": "Test Document body", "headline": "RETAKE", "slugline": "RETAKE"}
        """
        When we publish "123" with "publish" type and "published" state
        Then we get OK response
        When we publish "#REWRITE_ID#" with "publish" type and "published" state
        When we get "/published"
        Then we get existing resource
        """
        {"_items" : [{"_id": "#REWRITE_ID#", "anpa_take_key": "update"}]}
        """

    @auth
    Scenario: Fail to publish rewrite when original story is not yet published
        Given the "validators"
        """
          [
          {
              "schema": {},
              "type": "text",
              "act": "publish",
              "_id": "publish_text"
          },
          {
              "_id": "publish_composite",
              "act": "publish",
              "type": "composite",
              "schema": {}
          }
          ]
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body"}]
        """
        When we post to "/products" with success
        """
        {
          "name":"prod-1","codes":"abc,xyz", "product_type": "both"
        }
        """
        And we post to "/subscribers" with success
        """
        {
          "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "products": ["#products._id#"],
          "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
        }
        """
        When we rewrite "123"
        """
        {"desk_id": "#desks._id#"}
        """
        And we patch "archive/#REWRITE_ID#"
        """
        {"abstract": "test", "body_html": "Test Document body", "headline": "RETAKE", "slugline": "RETAKE"}
        """
        When we publish "#REWRITE_ID#" with "publish" type and "published" state
        Then we get error 400
        """
        {
          "_status": "ERR",
          "_issues": {"validator exception": "400: Can't publish update until original story is published."}
        }
        """

    @auth
    Scenario: Cannot create rewrite of a rewrite if the original rewrite is not published
        Given the "validators"
        """
          [
          {
              "schema": {},
              "type": "text",
              "act": "publish",
              "_id": "publish_text"
          },
          {
              "_id": "publish_composite",
              "act": "publish",
              "type": "composite",
              "schema": {}
          }
          ]
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body"}]
        """
        When we post to "/products" with success
        """
        {
          "name":"prod-1","codes":"abc,xyz", "product_type": "both"
        }
        """
        And we post to "/subscribers" with success
        """
        {
          "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "products": ["#products._id#"],
          "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
        }
        """
        Then we get OK response
        When we rewrite "123"
        """
        {"desk_id": "#desks._id#"}
        """
        And we patch "archive/#REWRITE_ID#"
        """
        {"abstract": "test", "body_html": "Test Document body", "headline": "RETAKE", "slugline": "RETAKE"}
        """
        Then we get OK response
        When we rewrite "#REWRITE_ID#"
        """
        {"desk_id": "#desks._id#"}
        """
        Then we get error 400
        """
        {"_status": "ERR",
         "_message": "Rewrite is not published. Cannot rewrite the story again."}
        """

    @auth
    @content_type
    Scenario: Archive rewrite should preserve profile and metadata specific to that profile
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{"type":"text", "headline": "Rewrite preserves profile", "_id": "xyz", "profile": "story",
          "subject": [{"scheme": "territory", "qcode": "paterritory:uk", "name": "UK"}],
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
           "keywords": ["UK"], "target_regions": [{"name": "Test", "qcode": "Test", "allow": true}]
           }]
        """
        When we rewrite "xyz"
        """
        {"desk_id": "#desks._id#"}
        """
        And we get "/archive/#REWRITE_ID#"
        Then we get existing resource
        """
        {
          "type":"text", "headline": "Rewrite preserves profile", "_id": "#REWRITE_ID#", "profile": "story",
          "subject": [{"scheme": "territory", "qcode": "paterritory:uk", "name": "UK"}],
          "task": {"desk": "#desks._id#"}, "rewrite_of": "xyz",
          "keywords": ["UK"], "target_regions": [{"name": "Test", "qcode": "Test", "allow": true}]
        }
        """

    @auth @vocabulary
    Scenario: Rewrite should be published to previously sent subscriber where rewrite is created before original is published.
        Given the "validators"
        """
          [
          {
              "schema": {},
              "type": "text",
              "act": "publish",
              "_id": "publish_text"
          },
          {
              "_id": "publish_composite",
              "act": "publish",
              "type": "composite",
              "schema": {}
          }
          ]
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body"}]
        """
        When we post to "/filter_conditions" with success
        """
        [{"name": "Statistics", "field": "subject", "operator": "in", "value": "17004000"}]
        """
        And we post to "/content_filters" with success
        """
        [{
            "name": "stats",
            "content_filter": [{"expression" : {"fc" : ["#filter_conditions._id#"]}}]
         }]
        """
        And we post to "/products" with success
        """
        {
            "name":"prod-1","codes":"abc,xyz",
            "content_filter": {
                "filter_type": "permitting",
                "filter_id": "#content_filters._id#"
            }, "product_type": "both"
        }
        """
        And we post to "/subscribers" with "digital" and success
        """
            {
                "name":"digital","media_type":"media",
                "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10},
                "email": "test@test.com",
                "products": ["#products._id#"],
                "destinations":[
                    {"name":"Test","format": "nitf",
                    "delivery_type":"email","config":{"recipients":"test@test.com"}}
                ]
            }
        """
        And we post to "/subscribers" with "wire" and success
        """
            {
                "name":"wire","media_type":"media",
                "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10},
                "email": "test@test.com",
                "products": ["#products._id#"],
                "destinations":[
                    {"name":"Test","format": "nitf",
                    "delivery_type":"email","config":{"recipients":"test@test.com"}}
                ]
            }
        """
        When we rewrite "123"
        """
        {"desk_id": "#desks._id#"}
        """
        And we patch "archive/#REWRITE_ID#"
        """
        {"abstract": "test", "body_html": "Test Document body",
        "headline": "Test Headline Update", "slugline": "Update",
        "subject":[{"qcode": "01000000", "name": "arts, culture and entertainment"}]}
        """
        Then we get OK response
        When we publish "123" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 2 items
        """
        {
            "_items": [
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#digital#", "item_id": "123", "item_version": 2},
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "123", "item_version": 2}
            ]
        }
        """
        When we publish "#REWRITE_ID#" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 4 items
        """
        {
            "_items": [
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "123", "item_version": 2},
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "#REWRITE_ID#", "item_version": 3}
            ]
        }
        """

    @auth @vocabulary
    Scenario: Rewrite should be published to previously sent subscriber where rewrite is created after original is published.
        Given the "validators"
        """
            [
                {
                  "schema": {},
                  "type": "text",
                  "act": "publish",
                  "_id": "publish_text"
                },
                {
                  "_id": "publish_composite",
                  "act": "publish",
                  "type": "composite",
                  "schema": {}
                }
            ]
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body"}]
        """
        When we post to "/filter_conditions" with success
        """
        [{"name": "Statistics", "field": "subject", "operator": "in", "value": "17004000"}]
        """
        And we post to "/content_filters" with success
        """
        [{
            "name": "stats",
            "content_filter": [{"expression" : {"fc" : ["#filter_conditions._id#"]}}]
         }]
        """
        And we post to "/products" with success
        """
        {
            "name":"prod-1","codes":"abc,xyz",
            "content_filter": {
                "filter_type": "permitting",
                "filter_id": "#content_filters._id#"
            }, "product_type": "both"
        }
        """
        And we post to "/subscribers" with "digital" and success
        """
            {
                "name":"digital","media_type":"media",
                "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10},
                "email": "test@test.com",
                "products": ["#products._id#"],
                "destinations":[
                    {"name":"Test","format": "nitf",
                    "delivery_type":"email","config":{"recipients":"test@test.com"}}
                ]
            }
        """
        And we post to "/subscribers" with "wire" and success
        """
            {
                "name":"wire","media_type":"media",
                "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10},
                "email": "test@test.com",
                "products": ["#products._id#"],
                "destinations":[
                    {"name":"Test","format": "nitf",
                    "delivery_type":"email","config":{"recipients":"test@test.com"}}
                ]
            }
        """
        When we publish "123" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 2 items
        """
        {
            "_items": [
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#digital#", "item_id": "123", "item_version": 2},
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "123", "item_version": 2}
            ]
        }
        """
        When we rewrite "123"
        """
        {"desk_id": "#desks._id#"}
        """
        And we patch "archive/#REWRITE_ID#"
        """
        {"abstract": "test", "body_html": "Test Document body",
        "headline": "Test Headline Update", "slugline": "Update",
        "subject":[{"qcode": "01000000", "name": "arts, culture and entertainment"}]}
        """
        Then we get OK response
        When we publish "#REWRITE_ID#" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 4 items
        """
        {
            "_items": [
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "123", "item_version": 2},
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "#REWRITE_ID#", "item_version": 3}
            ]
        }
        """

    @auth @vocabulary
    Scenario: Rewrite should be published to previously sent subscriber where original is only published to digital
        Given the "validators"
        """
          [
          {
              "schema": {},
              "type": "text",
              "act": "publish",
              "_id": "publish_text"
          },
          {
              "_id": "publish_composite",
              "act": "publish",
              "type": "composite",
              "schema": {}
          }
          ]
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body"}]
        """
        When we post to "/filter_conditions" with "fc1" and success
        """
        [{"name": "Statistics", "field": "subject", "operator": "in", "value": "17004000"}]
        """
        And we post to "/content_filters" with "cf1" and success
        """
        [{
            "name": "stats",
            "content_filter": [{"expression" : {"fc" : ["#fc1#"]}}]
         }]
        """
        And we post to "/products" with "product1" and success
        """
        {
            "name":"prod-1","codes":"abc,xyz",
            "content_filter": {
                "filter_type": "permitting",
                "filter_id": "#cf1#"
            }, "product_type": "both"
        }
        """
        When we post to "/filter_conditions" with "fc2" and success
        """
        [{"name": "entertainment", "field": "subject", "operator": "in", "value": "01000000"}]
        """
        And we post to "/content_filters" with "cf2" and success
        """
        [{
            "name": "entertainment",
            "content_filter": [{"expression" : {"fc" : ["#fc2#"]}}]
         }]
        """
        And we post to "/products" with "product2" and success
        """
        {
            "name":"prod-2","codes":"abc,xyz",
            "content_filter": {
                "filter_type": "permitting",
                "filter_id": "#cf2#"
            }, "product_type": "both"
        }
        """
        And we post to "/subscribers" with "digital" and success
        """
            {
                "name":"digital","media_type":"media",
                "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10},
                "email": "test@test.com",
                "products": ["#product1#"],
                "destinations":[
                    {"name":"Test","format": "nitf",
                    "delivery_type":"email","config":{"recipients":"test@test.com"}}
                ]
            }
        """
        And we post to "/subscribers" with "wire" and success
        """
            {
                "name":"wire","media_type":"media",
                "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10},
                "email": "test@test.com",
                "products": ["#product2#"],
                "destinations":[
                    {"name":"Test","format": "nitf",
                    "delivery_type":"email","config":{"recipients":"test@test.com"}}
                ]
            }
        """
        When we publish "123" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 1 items
        """
        {
            "_items": [
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#digital#", "item_id": "123", "item_version": 2}
            ]
        }
        """
        When we rewrite "123"
        """
        {"desk_id": "#desks._id#"}
        """
        And we patch "archive/#REWRITE_ID#"
        """
        {"abstract": "test", "body_html": "Test Document body",
        "headline": "Test Headline Update", "slugline": "Update",
        "subject":[{"qcode": "01000000", "name": "arts, culture and entertainment"}]}
        """
        Then we get OK response
        When we publish "#REWRITE_ID#" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 3 items
        """
        {
            "_items": [
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#digital#", "item_id": "123", "item_version": 2},
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "#REWRITE_ID#", "item_version": 3}
            ]
        }
        """

    @auth @vocabulary
    Scenario: Rewrite should be published to previously sent subscriber where original is only published to wire
        Given the "validators"
        """
          [
          {
              "schema": {},
              "type": "text",
              "act": "publish",
              "_id": "publish_text"
          },
          {
              "_id": "publish_composite",
              "act": "publish",
              "type": "composite",
              "schema": {}
          }
          ]
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body"}]
        """
        When we post to "/filter_conditions" with "fc1" and success
        """
        [{"name": "Statistics", "field": "subject", "operator": "in", "value": "17004000"}]
        """
        And we post to "/content_filters" with "cf1" and success
        """
        [{
            "name": "stats",
            "content_filter": [{"expression" : {"fc" : ["#fc1#"]}}]
         }]
        """
        And we post to "/products" with "product1" and success
        """
        {
            "name":"prod-1","codes":"abc,xyz",
            "content_filter": {
                "filter_type": "permitting",
                "filter_id": "#cf1#"
            }, "product_type": "both"
        }
        """
        When we post to "/filter_conditions" with "fc2" and success
        """
        [{"name": "entertainment", "field": "subject", "operator": "in", "value": "01000000"}]
        """
        And we post to "/content_filters" with "cf2" and success
        """
        [{
            "name": "entertainment",
            "content_filter": [{"expression" : {"fc" : ["#fc2#"]}}]
         }]
        """
        And we post to "/products" with "product2" and success
        """
        {
            "name":"prod-2","codes":"abc,xyz",
            "content_filter": {
                "filter_type": "permitting",
                "filter_id": "#cf2#"
            }, "product_type": "both"
        }
        """
        And we post to "/subscribers" with "digital" and success
        """
            {
                "name":"digital","media_type":"media",
                "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10},
                "email": "test@test.com",
                "products": ["#product2#"],
                "destinations":[
                    {"name":"Test","format": "nitf",
                    "delivery_type":"email","config":{"recipients":"test@test.com"}}
                ]
            }
        """
        And we post to "/subscribers" with "wire" and success
        """
            {
                "name":"wire","media_type":"media",
                "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10},
                "email": "test@test.com",
                "products": ["#product1#"],
                "destinations":[
                    {"name":"Test","format": "nitf",
                    "delivery_type":"email","config":{"recipients":"test@test.com"}}
                ]
            }
        """
        When we publish "123" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 1 items
        """
        {
            "_items": [
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "123", "item_version": 2}
            ]
        }
        """
        When we rewrite "123"
        """
        {"desk_id": "#desks._id#"}
        """
        And we patch "archive/#REWRITE_ID#"
        """
        {"abstract": "test", "body_html": "Test Document body",
        "headline": "Test Headline Update", "slugline": "Update",
        "subject":[{"qcode": "01000000", "name": "arts, culture and entertainment"}]}
        """
        Then we get OK response
        When we publish "#REWRITE_ID#" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 3 items
        """
        {
            "_items": [
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "123", "item_version": 2},
              {"state": "pending", "content_type": "text", "item_id": "#REWRITE_ID#",
              "subscriber_id": "#digital#", "item_version": 3},
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "#REWRITE_ID#", "item_version": 3}
            ]
        }
        """

    @auth @vocabulary
    Scenario: Rewrite of Rewrite should be published to previously sent subscriber
        Given the "validators"
        """
          [
          {
              "schema": {},
              "type": "text",
              "act": "publish",
              "_id": "publish_text"
          },
          {
              "_id": "publish_composite",
              "act": "publish",
              "type": "composite",
              "schema": {}
          }
          ]
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body"}]
        """
        When we post to "/filter_conditions" with "fc1" and success
        """
        [{"name": "Statistics", "field": "subject", "operator": "in", "value": "17004000"}]
        """
        And we post to "/content_filters" with "cf1" and success
        """
        [{
            "name": "stats",
            "content_filter": [{"expression" : {"fc" : ["#fc1#"]}}]
         }]
        """
        And we post to "/products" with "product1" and success
        """
        {
            "name":"prod-1","codes":"abc,xyz",
            "content_filter": {
                "filter_type": "permitting",
                "filter_id": "#cf1#"
            }, "product_type": "both"
        }
        """
        When we post to "/filter_conditions" with "fc2" and success
        """
        [{"name": "entertainment", "field": "subject", "operator": "in", "value": "01000000"}]
        """
        And we post to "/content_filters" with "cf2" and success
        """
        [{
            "name": "entertainment",
            "content_filter": [{"expression" : {"fc" : ["#fc2#"]}}]
         }]
        """
        And we post to "/products" with "product2" and success
        """
        {
            "name":"prod-2","codes":"abc,xyz",
            "content_filter": {
                "filter_type": "permitting",
                "filter_id": "#cf2#"
            }, "product_type": "both"
        }
        """
        And we post to "/subscribers" with "digital" and success
        """
            {
                "name":"digital","media_type":"media",
                "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10},
                "email": "test@test.com",
                "products": ["#product2#"],
                "destinations":[
                    {"name":"Test","format": "nitf",
                    "delivery_type":"email","config":{"recipients":"test@test.com"}}
                ]
            }
        """
        And we post to "/subscribers" with "wire" and success
        """
            {
                "name":"wire","media_type":"media",
                "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10},
                "email": "test@test.com",
                "products": ["#product1#"],
                "destinations":[
                    {"name":"Test","format": "nitf",
                    "delivery_type":"email","config":{"recipients":"test@test.com"}}
                ]
            }
        """
        When we publish "123" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 1 items
        """
        {
            "_items": [
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "123", "item_version": 2}
            ]
        }
        """
        When we rewrite "123"
        """
        {"desk_id": "#desks._id#"}
        """
        And we patch "archive/#REWRITE_ID#"
        """
        {"abstract": "test", "body_html": "Test Document body",
        "headline": "Test Headline Update", "slugline": "Update",
        "subject":[{"qcode": "01000000", "name": "arts, culture and entertainment"}]}
        """
        Then we get OK response
        And we store "rewrite1" with value "#REWRITE_ID#" to context
        When we publish "#REWRITE_ID#" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 3 items
        """
        {
            "_items": [
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "123", "item_version": 2},
              {"state": "pending", "content_type": "text", "item_id": "#rewrite1#",
              "subscriber_id": "#digital#", "item_version": 3},
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "#rewrite1#", "item_version": 3}
            ]
        }
        """
        When we rewrite "#rewrite1#"
        """
        {"desk_id": "#desks._id#"}
        """
        And we patch "archive/#REWRITE_ID#"
        """
        {"abstract": "test", "body_html": "Test Document body",
        "headline": "Test Headline Update", "slugline": "Update",
        "subject":[{"qcode": "04000000", "name": "Sports"}]}
        """
        Then we get OK response
        And we store "rewrite2" with value "#REWRITE_ID#" to context
        When we publish "#rewrite2#" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        And we get "/publish_queue"
        Then we get list with 5 items
        """
        {
            "_items": [
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "123", "item_version": 2},
              {"state": "pending", "content_type": "text",
              "item_id": "#rewrite1#", "subscriber_id": "#digital#", "item_version": 3},
              {"state": "pending", "content_type": "text", "subscriber_id": "#wire#",
              "item_id": "#rewrite1#", "item_version": 3},
              {"state": "pending", "content_type": "text", "item_id": "#rewrite2#",
              "subscriber_id": "#digital#", "item_version": 3},
              {"state": "pending", "content_type": "text",
              "subscriber_id": "#wire#", "item_id": "#rewrite2#", "item_version": 3}
            ]
        }
        """

    @auth
    Scenario: Rewrite a published content with reset priority flag
      Given the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "body_html": "Test Document body", "genre": [{"name": "Article", "qcode": "Article"}],
        "flags": {"marked_for_legal": true}, "priority": 2, "urgency": 2,
        "body_footer": "Suicide Call Back Service 1300 659 467",
        "place": [{"qcode" : "ACT", "world_region" : "Oceania", "country" : "Australia",
        "name" : "ACT", "state" : "Australian Capital Territory"}],
        "company_codes" : [{"qcode" : "1PG", "security_exchange" : "ASX", "name" : "1-PAGE LIMITED"}]
      }]
      """
      When we post to "/stages"
      """
      [
        {
        "name": "another stage",
        "description": "another stage",
        "task_status": "in_progress",
        "desk": "#desks._id#"
        }
      ]
      """
      And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#stages._id#"}}]
        """
      Then we get OK response
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "published", "task":{"desk": "#desks._id#", "stage": "#stages._id#"}}
      """
      And we reset priority flag for updated articles
      When we rewrite "123"
      """
      {"desk_id": "#desks._id#"}
      """
      Then we get OK response
      When we get "/archive/#REWRITE_ID#"
      Then we get existing resource
      """
      {"_id": "#REWRITE_ID#", "priority": 6, "urgency": 2}
      """

    @auth
    Scenario: Associate a story as update with reset priority flag
      Given the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "body_html": "Test Document body", "genre": [{"name": "Article", "value": "Article"}],
        "flags": {"marked_for_legal": true},
        "body_footer": "Suicide Call Back Service 1300 659 467",
        "place": [{"qcode" : "ACT", "world_region" : "Oceania", "country" : "Australia",
        "name" : "ACT", "state" : "Australian Capital Territory"}],
        "company_codes" : [{"qcode" : "1PG", "security_exchange" : "ASX", "name" : "1-PAGE LIMITED"}]
      },{"guid": "456", "type": "text", "headline": "test",
        "_current_version": 1, "state": "submitted", "priority": 2,
         "subject":[{"qcode": "01000000", "name": "arts, culture and entertainment"}]}]
      """
      When we post to "/stages"
      """
      [
        {
        "name": "another stage",
        "description": "another stage",
        "task_status": "in_progress",
        "desk": "#desks._id#"
        }
      ]
      """
      And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#stages._id#"}}]
        """
      Then we get OK response
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we publish "123" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "published", "task":{"desk": "#desks._id#", "stage": "#stages._id#"}}
      """
      When we get "/published"
      Then we get existing resource
      """
      {"_items" : [{"_id": "123", "guid": "123", "headline": "test", "_current_version": 3, "state": "published",
        "task": {"desk": "#desks._id#", "stage": "#stages._id#", "user": "#CONTEXT_USER_ID#"}}]}
      """
      And we reset priority flag for updated articles
      When we rewrite "123"
      """
      {"update": {"_id": "456", "type": "text", "headline": "test",
      "_current_version": 1, "state": "submitted", "priority": 2,
      "subject":[{"qcode": "01000000", "name": "arts, culture and entertainment"}]}}
      """
      When we get "/published"
      Then we get existing resource
      """
      {"_items" : [{"_id": "123", "rewritten_by": "456"}]}
      """
      When we get "/archive/456"
      Then we get existing resource
      """
      {"_id": "456", "anpa_take_key": "update",
       "rewrite_of": "123", "priority": 6,
       "subject":[{"qcode": "17004000", "name": "Statistics"},
       {"qcode": "01000000", "name": "arts, culture and entertainment"}]}
      """
      When we get "/archive/123"
      Then we get existing resource
      """
      {"_id": "123", "rewritten_by": "456", "place": [{"qcode" : "ACT"}]}
      """

    @auth
    Scenario: Rewrite un-published content from agency preserves source
      Given "desks"
      """
      [{"name": "Sports"}]
      """
      And "ingest_providers"
      """
      [{"name": "agency", "source": "YYY"}]
      """
      And the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "body_html": "Test Document body", "genre": [{"name": "Article", "qcode": "Article"}],
        "flags": {"marked_for_legal": true},
        "body_footer": "Suicide Call Back Service 1300 659 467",
        "place": [{"qcode" : "ACT", "world_region" : "Oceania", "country" : "Australia",
        "name" : "ACT", "state" : "Australian Capital Territory"}],
        "target_subscribers": [{"_id": "abc"}],
        "company_codes" : [{"qcode" : "1PG", "security_exchange" : "ASX", "name" : "1-PAGE LIMITED"}],
        "ingest_provider": "#ingest_providers._id#", "source": "YYY"
      }]
      """
      When we post to "/stages"
      """
      [
        {
        "name": "another stage",
        "description": "another stage",
        "task_status": "in_progress",
        "desk": "#desks._id#"
        }
      ]
      """
      When we rewrite "123"
      """
      {"desk_id": "#desks._id#"}
      """
      When we get "/archive/#REWRITE_ID#"
      Then there is no "body_html" in response
      And we get existing resource
      """
      {
        "_id": "#REWRITE_ID#",
        "rewrite_of": "123",
        "headline": "test",
        "rewrite_sequence": 1,
        "_current_version": 1,
        "source": "YYY"
      }
      """
      When we get "/archive/123"
      Then we get existing resource
      """
      {
        "_id": "123",
        "rewritten_by": "#REWRITE_ID#",
        "place": [{"qcode" : "ACT"}],
        "target_subscribers": [{"_id": "abc"}],
        "source": "YYY"
      }
      """

    @auth
    Scenario: Associate an update preserves original source
      Given "desks"
      """
      [{"name": "Sports"}]
      """
      And "ingest_providers"
      """
      [
        { "_id": "1", "name": "agency", "source": "YYY"},
        { "_id": "2", "name": "agency", "source": "XXX"}
      ]
      """
      And the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "body_html": "Test Document body", "genre": [{"name": "Article", "qcode": "Article"}],
        "flags": {"marked_for_legal": true},
        "body_footer": "Suicide Call Back Service 1300 659 467",
        "place": [{"qcode" : "ACT", "world_region" : "Oceania", "country" : "Australia",
        "name" : "ACT", "state" : "Australian Capital Territory"}],
        "target_subscribers": [{"_id": "abc"}],
        "company_codes" : [{"qcode" : "1PG", "security_exchange" : "ASX", "name" : "1-PAGE LIMITED"}],
        "ingest_provider": "1", "source": "YYY"
      },
      {"guid": "456", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "body_html": "Test Document body", "genre": [{"name": "Article", "qcode": "Article"}],
        "flags": {"marked_for_legal": true},
        "body_footer": "Suicide Call Back Service 1300 659 467",
        "place": [{"qcode" : "ACT", "world_region" : "Oceania", "country" : "Australia",
        "name" : "ACT", "state" : "Australian Capital Territory"}],
        "target_subscribers": [{"_id": "abc"}],
        "company_codes" : [{"qcode" : "1PG", "security_exchange" : "ASX", "name" : "1-PAGE LIMITED"}],
        "ingest_provider": "2", "source": "XXX"
      }
      ]
      """
      When we post to "/stages"
      """
      [
        {
        "name": "another stage",
        "description": "another stage",
        "task_status": "in_progress",
        "desk": "#desks._id#"
        }
      ]
      """
      When we rewrite "123"
      """
      {
        "update": {"_id": "456", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "body_html": "Test Document body", "genre": [{"name": "Article", "qcode": "Article"}],
        "flags": {"marked_for_legal": true},
        "body_footer": "Suicide Call Back Service 1300 659 467",
        "place": [{"qcode" : "ACT", "world_region" : "Oceania", "country" : "Australia",
        "name" : "ACT", "state" : "Australian Capital Territory"}],
        "target_subscribers": [{"_id": "abc"}],
        "company_codes" : [{"qcode" : "1PG", "security_exchange" : "ASX", "name" : "1-PAGE LIMITED"}],
        "ingest_provider": "2", "source": "XXX"
        }
      }
      """
      When we get "/archive/#REWRITE_ID#"
      Then we get existing resource
      """
      {
        "_id": "#REWRITE_ID#",
        "rewrite_of": "123",
        "headline": "test",
        "rewrite_sequence": 1,
        "_current_version": 1,
        "source": "XXX",
        "ingest_provider": "2", "source": "XXX"
      }
      """
      When we get "/archive/123"
      Then we get existing resource
      """
      {
        "_id": "123",
        "rewritten_by": "#REWRITE_ID#",
        "place": [{"qcode" : "ACT"}],
        "target_subscribers": [{"_id": "abc"}],
        "ingest_provider": "1", "source": "YYY"
      }
      """

    @auth
    Scenario: Do not overwrite existing item associations
      Given the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      Given "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [
          {
              "guid": "123",
              "_id": "123",
              "type": "text",
              "headline": "test original",
              "_current_version": 1,
              "state": "draft",
              "task": {
                  "desk": "#desks._id#",
                  "stage": "#desks.incoming_stage#",
                  "user": "#CONTEXT_USER_ID#"
              },
              "subject": [
                  {
                      "qcode": "17004000",
                      "name": "Statistics"
                  }
              ],
              "body_html": "Test Document body original",
              "genre": [
                  {
                      "name": "Article",
                      "qcode": "Article"
                  }
              ],
              "body_footer": "Original Suicide Call Back Service 1300 659 467",
              "associations": {
                  "editor_0": {
                      "guid": "123",
                      "type": "picture",
                      "slugline": "123",
                      "state": "in_progress",
                      "headline": "some headline",
                      "renditions": {
                          "original": {}
                      }
                  },
                  "editor_2": {
                      "guid": "1234",
                      "type": "picture",
                      "slugline": "1234",
                      "state": "in_progress",
                      "headline": "some headline",
                      "renditions": {
                          "original": {}
                      }
                  }
              }
          },
          {
              "guid": "456",
              "_id": "456",
              "type": "text",
              "headline": "test",
              "_current_version": 1,
              "state": "draft",
              "task": {
                  "desk": "#desks._id#",
                  "stage": "#desks.incoming_stage#",
                  "user": "#CONTEXT_USER_ID#"
              },
              "subject": [
                  {
                      "qcode": "17004000",
                      "name": "Statistics"
                  }
              ],
              "body_html": "Test Document body",
              "genre": [
                  {
                      "name": "Music",
                      "qcode": "Music"
                  }
              ],
              "body_footer": "Suicide Call Back Service 1300 659 467",
              "associations": {
                  "editor_0": {
                      "guid": "456",
                      "type": "picture",
                      "slugline": "456",
                      "state": "in_progress",
                      "headline": "some headline",
                      "renditions": {
                          "original": {}
                      }
                  },
                  "editor_1": {
                      "guid": "786",
                      "type": "picture",
                      "slugline": "786",
                      "state": "in_progress",
                      "headline": "some headline",
                      "renditions": {
                          "original": {}
                      }
                  }
              }
          }
      ]
      """
      When we rewrite "123"
      """
      {
          "update": {
              "guid": "456",
              "_id": "456",
              "type": "text",
              "headline": "test",
              "_current_version": 1,
              "state": "draft",
              "task": {
                  "desk": "#desks._id#",
                  "stage": "#desks.incoming_stage#",
                  "user": "#CONTEXT_USER_ID#"
              },
              "subject": [
                  {
                      "qcode": "17004000",
                      "name": "Statistics"
                  }
              ],
              "body_html": "Test Document body",
              "genre": [
                  {
                      "name": "Music",
                      "qcode": "Music"
                  }
              ],
              "body_footer": "Suicide Call Back Service 1300 659 467",
              "associations": {
                  "editor_0": {
                      "guid": "456",
                      "type": "picture",
                      "slugline": "456",
                      "state": "in_progress",
                      "headline": "some headline",
                      "renditions": {
                          "original": {}
                      }
                  },
                  "editor_1": {
                      "guid": "786",
                      "type": "picture",
                      "slugline": "786",
                      "state": "in_progress",
                      "headline": "some headline",
                      "renditions": {
                          "original": {}
                      }
                  }
              }
          }
      }
      """
      When we get "/archive/#REWRITE_ID#"
      Then we get existing resource
      """
      {
          "_id": "456",
          "rewrite_of": "123",
          "headline": "test",
          "rewrite_sequence": 1,
          "_current_version": 1,
          "body_html": "Test Document body",
          "associations": {
              "editor_0": {
                  "guid": "456",
                  "type": "picture",
                  "slugline": "456",
                  "state": "in_progress",
                  "headline": "some headline",
                  "renditions": {
                      "original": {}
                  }
              },
              "editor_1": {
                  "guid": "786",
                  "type": "picture",
                  "slugline": "786",
                  "state": "in_progress",
                  "headline": "some headline",
                  "renditions": {
                      "original": {}
                  }
              },
              "editor_2": {
                  "guid": "1234",
                  "type": "picture",
                  "slugline": "1234",
                  "state": "in_progress",
                  "headline": "some headline",
                  "renditions": {
                      "original": {}
                  }
              }
          }
      }
      """

    @auth
    Scenario: Add association if existing item does not have associations
      Given the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      Given "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [
          {
              "guid": "123",
              "_id": "123",
              "type": "text",
              "headline": "test original",
              "_current_version": 1,
              "state": "draft",
              "task": {
                  "desk": "#desks._id#",
                  "stage": "#desks.incoming_stage#",
                  "user": "#CONTEXT_USER_ID#"
              },
              "subject": [
                  {
                      "qcode": "17004000",
                      "name": "Statistics"
                  }
              ],
              "body_html": "Test Document body original",
              "genre": [
                  {
                      "name": "Article",
                      "qcode": "Article"
                  }
              ],
              "body_footer": "Original Suicide Call Back Service 1300 659 467",
              "associations": {
                  "editor_0": {
                      "guid": "123",
                      "type": "picture",
                      "slugline": "123",
                      "state": "in_progress",
                      "headline": "some headline",
                      "renditions": {
                          "original": {}
                      }
                  },
                  "editor_1": {
                      "guid": "786",
                      "type": "picture",
                      "slugline": "786",
                      "state": "in_progress",
                      "headline": "some headline",
                      "renditions": {
                          "original": {}
                      }
                  }
              }
          },
          {
              "guid": "456",
              "_id": "456",
              "type": "text",
              "headline": "test",
              "_current_version": 1,
              "state": "draft",
              "task": {
                  "desk": "#desks._id#",
                  "stage": "#desks.incoming_stage#",
                  "user": "#CONTEXT_USER_ID#"
              },
              "subject": [
                  {
                      "qcode": "17004000",
                      "name": "Statistics"
                  }
              ],
              "body_html": "Test Document body",
              "genre": [
                  {
                      "name": "Music",
                      "qcode": "Music"
                  }
              ],
              "body_footer": "Suicide Call Back Service 1300 659 467"
          }
      ]
      """
      When we rewrite "123"
      """
      {
          "update": {
              "guid": "456",
              "_id": "456",
              "type": "text",
              "headline": "test",
              "_current_version": 1,
              "state": "draft",
              "task": {
                  "desk": "#desks._id#",
                  "stage": "#desks.incoming_stage#",
                  "user": "#CONTEXT_USER_ID#"
              },
              "subject": [
                  {
                      "qcode": "17004000",
                      "name": "Statistics"
                  }
              ],
              "body_html": "Test Document body",
              "genre": [
                  {
                      "name": "Music",
                      "qcode": "Music"
                  }
              ],
              "body_footer": "Suicide Call Back Service 1300 659 467"
          }
      }
      """
      When we get "/archive/#REWRITE_ID#"
      Then we get existing resource
      """
      {
          "_id": "456",
          "rewrite_of": "123",
          "headline": "test",
          "rewrite_sequence": 1,
          "_current_version": 1,
          "body_html": "Test Document body",
          "associations": {
              "editor_0": {
                  "guid": "123",
                  "type": "picture",
                  "slugline": "123",
                  "state": "in_progress",
                  "headline": "some headline",
                  "renditions": {
                      "original": {}
                  }
              },
              "editor_1": {
                  "guid": "786",
                  "type": "picture",
                  "slugline": "786",
                  "state": "in_progress",
                  "headline": "some headline",
                  "renditions": {
                      "original": {}
                  }
              }
          }
      }
      """

    @auth
    Scenario: Do not overwrite existing item flags
      Given the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      Given "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [
          {
              "guid": "123",
              "_id": "123",
              "type": "text",
              "headline": "test original",
              "_current_version": 1,
              "state": "draft",
              "task": {
                  "desk": "#desks._id#",
                  "stage": "#desks.incoming_stage#",
                  "user": "#CONTEXT_USER_ID#"
              },
              "flags": {
                "marked_for_legal": true,
                "marked_for_sms": false,
                "marked_not_for_publication": false
              },
              "subject": [
                  {
                      "qcode": "17004000",
                      "name": "Statistics"
                  }
              ],
              "body_html": "Test Document body original",
              "genre": [
                  {
                      "name": "Article",
                      "qcode": "Article"
                  }
              ],
              "body_footer": "Original Suicide Call Back Service 1300 659 467"
          },
          {
              "guid": "456",
              "_id": "456",
              "type": "text",
              "headline": "test",
              "_current_version": 1,
              "state": "draft",
              "task": {
                  "desk": "#desks._id#",
                  "stage": "#desks.incoming_stage#",
                  "user": "#CONTEXT_USER_ID#"
              },
              "subject": [
                  {
                      "qcode": "17004000",
                      "name": "Statistics"
                  }
              ],
              "body_html": "Test Document body",
              "sms_message": "update story sms",
              "flags": {
                "marked_for_legal": false,
                "marked_for_sms": true,
                "marked_not_for_publication": false
              },
              "genre": [
                  {
                      "name": "Music",
                      "qcode": "Music"
                  }
              ],
              "body_footer": "Suicide Call Back Service 1300 659 467"
          }
      ]
      """
      When we rewrite "123"
      """
      {
          "update": {
              "guid": "456",
              "_id": "456",
              "type": "text",
              "headline": "test",
              "_current_version": 1,
              "state": "draft",
              "task": {
                  "desk": "#desks._id#",
                  "stage": "#desks.incoming_stage#",
                  "user": "#CONTEXT_USER_ID#"
              },
              "subject": [
                  {
                      "qcode": "17004000",
                      "name": "Statistics"
                  }
              ],
              "body_html": "Test Document body",
              "sms_message": "update story sms",
              "flags": {
                "marked_for_legal": false,
                "marked_for_sms": true,
                "marked_not_for_publication": false
              },
              "genre": [
                  {
                      "name": "Music",
                      "qcode": "Music"
                  }
              ],
              "body_footer": "Suicide Call Back Service 1300 659 467"
          }
      }
      """
      When we get "/archive/#REWRITE_ID#"
      Then we get existing resource
      """
      {
          "_id": "456",
          "rewrite_of": "123",
          "headline": "test",
          "rewrite_sequence": 1,
          "_current_version": 1,
          "body_html": "Test Document body",
          "sms_message": "update story sms",
          "flags": {
            "marked_for_legal": true,
            "marked_for_sms": true,
            "marked_not_for_publication": false
          }
      }
      """

    @auth
    Scenario: Can create multiple rewrites if enabled
        Given config update
        """
        {"WORKFLOW_ALLOW_MULTIPLE_UPDATES": true}
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body"}]
        """
        When we rewrite "123"
        """
        {"desk_id": "#desks._id#"}
        """
        Then we get OK response
        When we rewrite "#REWRITE_ID#"
        """
        {"desk_id": "#desks._id#"}
        """
        Then we get OK response
        When we rewrite "#REWRITE_ID#"
        """
        {"desk_id": "#desks._id#"}
        """
        Then we get OK response
