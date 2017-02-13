Feature: Take Package Publishing

    @auth
    Scenario: Publish the second take before the first fails
      Given the "validators"
      """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And empty "ingest"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      When we post to "archive"
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "test1",
          "slugline": "comics",
          "anpa_take_key": "Take",
          "state": "draft",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "target_subscribers": [{"_id": "abc"}],
          "body_html": "Take-1"
      }]
      """
      And we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE"
      """
      {
          "type": "text",
          "headline": "test1",
          "slugline": "comics",
          "anpa_take_key": "Take=2",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#",
          "target_subscribers": [{"_id": "abc"}]
      }
      """
      When we patch "/archive/#TAKE#"
      """
      {"body_html": "Take-2"}
      """
      And we post to "/archive/#TAKE#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      And we get "/archive"
      Then we get list with 3 items
      """
      {
        "_items": [
          {"_id": "123", "type": "text", "anpa_take_key": "Take",
           "takes": {"_id": "#TAKE_PACKAGE#", "type": "composite", "package_type": "takes"}},
          {"_id": "#TAKE#", "type": "text", "anpa_take_key": "Take=2",
           "takes": {"_id": "#TAKE_PACKAGE#", "type": "composite", "package_type": "takes"}},
          {"_id": "#TAKE_PACKAGE#", "type": "composite"}
        ]
      }
      """
      When we publish "#TAKE#" with "publish" type and "published" state
      Then we get response code 400
      """
      {
          "_issues": {"validator exception": "500: Failed to publish the item: PublishQueueError Error 9006 - Previous take is either not published or killed"}
      }
      """

    @auth
    Scenario: Publish the very first take before the second
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And empty "ingest"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
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
      And we post to "archive" with success
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "Take-1 headline",
          "abstract": "Take-1 abstract",
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "body_html": "Take-1",
          "state": "draft",
          "slugline": "Take-1 slugline",
          "urgency": "4",
          "pubstatus": "usable",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "anpa_category": [{"qcode": "A", "name": "Sport"}],
          "anpa_take_key": "Take"
      }]
      """
      And we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE"
      """
      {
          "type": "text",
          "headline": "Take-1 headline",
          "slugline": "Take-1 slugline",
          "anpa_take_key": "Take=2",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we patch "/archive/#TAKE#"
      """
      {"body_html": "Take-2"}
      """
      And we post to "/archive/#TAKE#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      And we get "/archive"
      Then we get list with 3 items
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we get "/published"
      Then we get existing resource
      """
      {
          "_items": [
              {
                  "_current_version": 3,
                  "state": "published",
                  "body_html": "Take-1"
              },
              {
                  "_current_version": 2,
                  "state": "published",
                  "type": "composite",
                  "package_type": "takes",
                  "body_html": "Take-1"
              }
          ]
      }
      """

    @auth
    Scenario: Publish the second take after the first
      Given the "validators"
      """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
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
      When we post to "archive" with success
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "Take-1 headline",
          "abstract": "Take-1 abstract",
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "body_html": "Take-1",
          "state": "draft",
          "slugline": "Take-1 slugline",
          "urgency": "4",
          "pubstatus": "usable",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "anpa_category": [{"qcode": "A", "name": "Sport"}],
          "anpa_take_key": "Take"
      }]
      """
      And we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE"
      """
      {
          "type": "text",
          "headline": "Take-1 headline",
          "slugline": "Take-1 slugline",
          "anpa_take_key": "Take=2",
          "abstract": "__no_value__",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we patch "/archive/#TAKE#"
      """
      {"body_html": "Take-2", "headline": "Take-2 headline", "slugline": "Take-2 slugline"}
      """
      And we post to "/archive/#TAKE#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      And we get "/archive"
      Then we get list with 3 items
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we get "/archive/#TAKE_PACKAGE#"
      Then we get existing resource
      """
      {
          "type": "composite",
          "package_type": "takes",
          "headline": "Take-1 headline",
          "slugline": "Take-1 slugline",
          "abstract": "Take-1 abstract"
      }
      """
      When we publish "#TAKE#" with "publish" type and "published" state
      Then we get OK response
      When we get "/archive/#TAKE_PACKAGE#"
      Then we get existing resource
      """
      {
          "type": "composite",
          "package_type": "takes",
          "headline": "Take-2 headline",
          "slugline": "Take-2 slugline",
          "abstract": "Take-1 abstract"
      }
      """
      When we get "/published"
      Then we get existing resource
      """
      {
          "_items": [
              {
                  "_id": "123",
                  "_current_version": 3,
                  "state": "published",
                  "body_html": "Take-1",
                  "archive_item": {
                      "_id": "123",
                      "type": "text",
                      "takes": {
                         "_id": "#TAKE_PACKAGE#", "type": "composite"
                      }
                  }
              },
              {
                  "_current_version": 3,
                  "state": "published",
                  "type": "composite",
                  "package_type": "takes",
                  "abstract": "Take-1 abstract",
                  "body_html": "Take-1<br>Take-2",
                  "archive_item": {
                      "_id": "#TAKE_PACKAGE#"
                  }
              },
              {
                  "_id": "#TAKE#",
                  "_current_version": 4,
                  "state": "published",
                  "body_html": "Take-2",
                  "archive_item": {
                      "_id": "#TAKE#",
                      "type": "text",
                      "takes": {
                         "_id": "#TAKE_PACKAGE#", "type": "composite"
                      }
                  }
              }
          ]
      }
      """

    @auth
    Scenario: Publish takes package and kill takes
      Given the "validators"
      """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
         {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
      }
      """
      And we post to "/subscribers" with success
      """
      [{
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }, {
        "name":"Channel 4","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }]
      """
      And we post to "content_templates"
        """
          {
            "data": {
              "body_html": "<p>This is test story.<\/p>",
              "type": "text",
              "abstract": "This article has been removed",
              "headline": "Kill\/Takedown notice ~~~ Kill\/Takedown notice",
              "urgency": 1, "priority": 1,
              "anpa_take_key": "KILL\/TAKEDOWN"
            },
            "template_name": "kill",
            "template_type": "kill"
          }
        """
      When we post to "archive" with success
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "Take-1 headline",
          "abstract": "Take-1 abstract",
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "body_html": "Take-1",
          "state": "draft",
          "slugline": "Take-1 slugline",
          "urgency": "4",
          "pubstatus": "usable",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "anpa_category": [{"qcode": "A", "name": "Sport"}],
          "anpa_take_key": "Take"
      }]
      """
      And we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE2"
      """
      {
          "type": "text",
          "headline": "Take-1 headline",
          "slugline": "Take-1 slugline",
          "anpa_take_key": "Take=2",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we patch "/archive/#TAKE2#"
      """
      {"body_html": "Take-2", "abstract": "Take-2 Abstract", "slugline": "Take-2 slugline"}
      """
      And we post to "/archive/#TAKE2#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      When we post to "archive/#TAKE2#/link"
      """
      [{}]
      """
      Then we get next take as "TAKE3"
      """
      {
          "type": "text",
          "headline": "Take-1 headline",
          "slugline": "Take-2 slugline",
          "anpa_take_key": "Take=3",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we patch "/archive/#TAKE3#"
      """
      {"body_html": "Take-3", "abstract": "Take-3 Abstract", "slugline": "Take-3 slugline"}
      """
      And we post to "/archive/#TAKE3#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      And we get "/archive"
      Then we get list with 4 items
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we publish "#TAKE2#" with "publish" type and "published" state
      Then we get OK response
      When we publish "#TAKE3#" with "publish" type and "published" state
      Then we get OK response
      When we get "/published"
      Then we get existing resource
      """
      {
          "_items": [
              {
                  "_id": "123",
                  "_current_version": 3,
                  "state": "published",
                  "body_html": "Take-1",
                  "last_published_version": true
              },
              {
                  "_current_version": 5,
                  "state": "published",
                  "type": "composite",
                  "package_type": "takes",
                  "body_html": "Take-1<br>Take-2<br>Take-3",
                  "last_published_version": true
              },
              {
                  "_id": "#TAKE2#",
                  "_current_version": 4,
                  "state": "published",
                  "body_html": "Take-2",
                  "last_published_version": true
              },
              {
                  "_id": "#TAKE3#",
                  "_current_version": 4,
                  "state": "published",
                  "body_html": "Take-3",
                  "last_published_version": true
              }
          ]
      }
      """
      When we publish "#TAKE2#" with "kill" type and "killed" state
      """
      {"body_html": "Killed Story", "headline": "Kill/Takedown notice ~~~ Kill/Takedown notice"}
      """
      Then we get OK response
      When we get "/published"
      Then we get existing resource
      """
      {
          "_items": [
              {
                  "_id": "123",
                  "_current_version": 3,
                  "state": "published",
                  "body_html": "Take-1",
                  "last_published_version": false
              },
              {
                  "_id": "#archive.123.take_package#",
                  "_current_version": 3,
                  "state": "published",
                  "type": "composite",
                  "package_type": "takes",
                  "body_html": "Take-1",
                  "last_published_version": false
              },
              {
                  "_id": "#archive.123.take_package#",
                  "_current_version": 4,
                  "state": "published",
                  "type": "composite",
                  "package_type": "takes",
                  "body_html": "Take-1<br>Take-2",
                  "last_published_version": false
              },
              {
                  "_id": "#archive.123.take_package#",
                  "_current_version": 5,
                  "state": "published",
                  "type": "composite",
                  "package_type": "takes",
                  "body_html": "Take-1<br>Take-2<br>Take-3",
                  "last_published_version": false
              },
              {
                  "_id": "#TAKE2#",
                  "_current_version": 4,
                  "state": "published",
                  "body_html": "Take-2",
                  "last_published_version": false
              },
              {
                  "_id": "#TAKE3#",
                  "_current_version": 4,
                  "state": "published",
                  "body_html": "Take-3",
                  "last_published_version": false
              },
              {
                  "_id": "123",
                  "_current_version": 4,
                  "state": "killed",
                  "last_published_version": true,
                  "headline": "Kill/Takedown notice ~~~ Kill/Takedown notice",
                  "slugline": "Take-1 slugline"
              },
              {
                  "_id": "#TAKE2#",
                  "_current_version": 5,
                  "state": "killed",
                  "last_published_version": true,
                  "headline": "Kill/Takedown notice ~~~ Kill/Takedown notice",
                  "slugline": "Take-2 slugline"
              },
              {
                  "_id": "#TAKE3#",
                  "_current_version": 5,
                  "state": "killed",
                  "last_published_version": true,
                  "headline": "Kill/Takedown notice ~~~ Kill/Takedown notice",
                  "slugline": "Take-3 slugline"
              },
              {
                  "_id": "#archive.123.take_package#",
                  "_current_version": 6,
                  "state": "killed",
                  "type": "composite",
                  "package_type": "takes",
                  "headline": "Kill/Takedown notice ~~~ Kill/Takedown notice",
                  "slugline": "Take-2 slugline",
                  "last_published_version": true,
                  "groups": [
                    {"refs": [{"idRef" : "main"}], "id": "root"},
                    {"refs":[
                      {"_current_version": 4, "guid": "123"},
                      {"_current_version": 5, "guid": "#TAKE2#"},
                      {"_current_version": 5, "guid": "#TAKE3#"}
                    ],
                    "id" : "main"}
                  ]
              }
          ]
      }
      """
      When we get "/archive/123"
      Then we get text "Please kill story slugged Take-1 slugline" in response field "body_html"
      When we get "/archive/#TAKE2#"
      Then we get text "Please kill story slugged Take-2 slugline" in response field "body_html"
      When we get "/archive/#TAKE3#"
      Then we get text "Please kill story slugged Take-3 slugline" in response field "body_html"


    @auth @vocabulary
    Scenario: Publish subsequent takes to same wire clients as published before.
      Given the "validators"
      """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
         {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
         {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "filter_conditions"
      """
      [{"name": "sport", "field": "headline", "operator": "like", "value": "soccer"}]
      """
      And "content_filters"
      """
      [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer-only"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz",
        "content_filter":{"filter_id":"#content_filters._id#", "filter_type": "permitting"}
      }
      """
      And we post to "/subscribers" with "First_Wire_Subscriber" and success
      """
      [{
        "name":"Soccer Client1","media_type":"media", "subscriber_type": "wire",
        "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[
            {"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}
          ]
      }]
      """
      And we post to "/subscribers" with "Digital_Subscriber" and success
      """
      [{
        "name":"Soccer Client Digital","media_type":"media", "subscriber_type": "digital",
        "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[
            {"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}
          ]
      }]
      """
      And we post to "archive" with success
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "Take-1 soccer headline",
          "abstract": "Take-1 abstract",
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "body_html": "Take-1",
          "state": "draft",
          "slugline": "Take-1 slugline",
          "urgency": "4",
          "pubstatus": "usable",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "anpa_category": [{"qcode": "A", "name": "Sport"}],
          "anpa_take_key": "Take"
      }]
      """
      And we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE2"
      """
      {
          "type": "text",
          "headline": "Take-1 soccer headline",
          "slugline": "Take-1 slugline",
          "anpa_take_key": "Take=2",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we patch "/archive/#TAKE2#"
      """
      {"body_html": "Take-2", "abstract": "Take-2 Abstract"}
      """
      And we post to "/archive/#TAKE2#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      And we get "/archive"
      Then we get list with 3 items
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 2 items
      """
      {
          "_items": [
            {
              "item_id" : "123",
              "publishing_action" : "published",
              "content_type" : "text",
              "state" : "pending",
              "subscriber_id" : "#First_Wire_Subscriber#",
              "headline" : "Take-1 soccer headline=1",
              "item_version": 3
            },
            {
              "item_id" : "#archive.123.take_package#",
              "publishing_action" : "published",
              "content_type" : "composite",
              "state" : "pending",
              "subscriber_id" : "#Digital_Subscriber#",
              "headline" : "Take-1 soccer headline",
              "item_version": 2
            }
          ]
      }
      """
      When we post to "/subscribers" with "Second_Wire_Subscriber" and success
      """
      [{
        "name":"Soccer Client2","media_type":"media", "subscriber_type": "wire",
        "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[
            {"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}
          ]
      }]
      """
      When we publish "#TAKE2#" with "publish" type and "published" state
      Then we get OK response
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 4 items
      """
      {
          "_items": [
            {
              "item_id" : "123",
              "publishing_action" : "published",
              "content_type" : "text",
              "subscriber_id" : "#First_Wire_Subscriber#",
              "item_version": 3
            },
            {
              "item_id" : "#archive.123.take_package#",
              "publishing_action" : "published",
              "content_type" : "composite",
              "headline" : "Take-1 soccer headline",
              "subscriber_id" : "#Digital_Subscriber#",
              "item_version": 2
            },
            {
              "item_id" : "#TAKE2#",
              "publishing_action" : "published",
              "content_type" : "text",
              "subscriber_id" : "#First_Wire_Subscriber#",
              "item_version": 4
            },
            {
              "item_id" : "#archive.123.take_package#",
              "publishing_action" : "published",
              "content_type" : "composite",
              "headline" : "Take-1 soccer headline",
              "subscriber_id" : "#Digital_Subscriber#",
              "item_version": 3
            }
          ]
      }
      """
      When we publish "#TAKE2#" with "correct" type and "corrected" state
      Then we get OK response
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 6 items
      """
      {
          "_items": [
            {
              "item_id" : "123",
              "publishing_action" : "published",
              "content_type" : "text",
              "subscriber_id" : "#First_Wire_Subscriber#",
              "headline" : "Take-1 soccer headline=1",
              "item_version": 3
            },
            {
              "item_id" : "#archive.123.take_package#",
              "publishing_action" : "published",
              "content_type" : "composite",
              "headline" : "Take-1 soccer headline",
              "subscriber_id" : "#Digital_Subscriber#",
              "item_version": 2
            },
            {
              "item_id" : "#TAKE2#",
              "publishing_action" : "published",
              "content_type" : "text",
              "subscriber_id" : "#First_Wire_Subscriber#",
              "headline" : "Take-1 soccer headline=2",
              "item_version": 4
            },
            {
              "item_id" : "#archive.123.take_package#",
              "publishing_action" : "published",
              "content_type" : "composite",
              "headline" : "Take-1 soccer headline",
              "subscriber_id" : "#Digital_Subscriber#",
              "item_version": 3
            },
            {
              "item_id" : "#TAKE2#",
              "publishing_action" : "corrected",
              "content_type" : "text",
              "subscriber_id" : "#First_Wire_Subscriber#",
              "headline" : "Take-1 soccer headline=2",
              "item_version": 5
            },
            {
              "item_id" : "#archive.123.take_package#",
              "publishing_action" : "corrected",
              "content_type" : "composite",
              "headline" : "Take-1 soccer headline",
              "subscriber_id" : "#Digital_Subscriber#",
              "item_version": 4
            }
          ]
      }
      """

    @auth
    Scenario: Reopen a story published to digital subscriber by adding a new take
      Given the "validators"
      """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
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
      When we post to "archive" with success
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "Take-1 headline",
          "abstract": "Take-1 abstract",
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "body_html": "Take-1",
          "state": "draft",
          "slugline": "Take-1 slugline",
          "urgency": "4",
          "pubstatus": "usable",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "anpa_category": [{"qcode": "A", "name": "Sport"}],
          "anpa_take_key": null,
          "target_subscribers": [{"_id": "#subscribers._id#"}]
      }]
      """
      And we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we publish "#archive._id#" with "publish" type and "published" state
      And we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE"
      """
      {
          "type": "text",
          "headline": "Take-1 headline",
          "slugline": "Take-1 slugline",
          "anpa_take_key": "(reopens)=2",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#",
          "target_subscribers": [{"_id": "#subscribers._id#"}]
      }
      """
      When we patch "/archive/#TAKE#"
      """
      {"body_html": "Take-2", "abstract": "Take-2 Abstract"}
      """
      And we post to "/archive/#TAKE#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      And we get "/archive"
      Then we get list with 1 items
      When we publish "#TAKE#" with "publish" type and "published" state
      Then we get OK response
      When we get "/published"
      Then we get existing resource
      """
      {
          "_items": [
              {
                  "_id": "123",
                  "_current_version": 3,
                  "state": "published",
                  "body_html": "Take-1"
              },
              {
                  "_current_version": 2,
                  "state": "published",
                  "type": "composite",
                  "package_type": "takes",
                  "body_html": "Take-1"
              },
              {
                  "_current_version": 4,
                  "state": "published",
                  "type": "composite",
                  "package_type": "takes",
                  "body_html": "Take-1<br>Take-2"
              },
              {
                  "_current_version": 4,
                  "state": "published",
                  "body_html": "Take-2"
              }
          ]
      }
      """

    @auth
    Scenario: Reopen a story published to wire subscriber by adding a new take
      Given the "validators"
      """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      When we post to "archive" with success
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "Take-1 headline",
          "abstract": "Take-1 abstract",
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "body_html": "Take-1",
          "state": "draft",
          "slugline": "Take-1 slugline",
          "urgency": "4",
          "pubstatus": "usable",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "anpa_category": [{"qcode": "A", "name": "Sport"}],
          "anpa_take_key": "Take"
      }]
      """
      And we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we publish "#archive._id#" with "publish" type and "published" state
      And we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE"
      """
      {
          "type": "text",
          "headline": "Take-1 headline",
          "slugline": "Take-1 slugline",
          "anpa_take_key": "Take (reopens)=2",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we patch "/archive/#TAKE#"
      """
      {"body_html": "Take-2", "abstract": "Take-2 Abstract"}
      """
      And we post to "/archive/#TAKE#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      And we get "/archive"
      Then we get list with 1 items
      When we publish "#TAKE#" with "publish" type and "published" state
      Then we get OK response
      When we get "/published"
      Then we get existing resource
      """
      {
          "_items": [
              {
                  "type": "text",
                  "_current_version": 3,
                  "body_html": "Take-1"
              },
              {
                  "_current_version": 4,
                  "type": "composite",
                  "package_type": "takes",
                  "body_html": "Take-1<br>Take-2"
              },
              {
                  "type": "text",
                  "_current_version": 4,
                  "body_html": "Take-2"
              }
          ]
      }
      """

    @auth @vocabulary
    Scenario: Takes cannot be scheduled.
      Given the "validators"
      """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
         {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
         {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      When we post to "archive" with success
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "Take-1 soccer headline",
          "abstract": "Take-1 abstract",
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "body_html": "Take-1",
          "state": "draft",
          "slugline": "Take-1 slugline",
          "urgency": "4",
          "pubstatus": "usable",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "anpa_category": [{"qcode": "A", "name": "Sport"}],
          "anpa_take_key": "Take"
      }]
      """
      And we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE2"
      """
      {
          "type": "text",
          "headline": "Take-1 soccer headline",
          "slugline": "Take-1 slugline",
          "anpa_take_key": "Take=2",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we patch "/archive/#TAKE2#"
      """
      {"body_html": "Take-2", "abstract": "Take-2 Abstract"}
      """
      And we post to "/archive/#TAKE2#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      And we get "/archive"
      Then we get list with 3 items
      When we patch "/archive/123"
      """
      {"publish_schedule": "2099-05-30T10:00:00+00:00"}
      """
      Then we get error 400
      """
      {"_issues": {"validator exception": "400: Takes cannot be scheduled."}, "_status": "ERR"}
      """
      When we patch "/archive/#TAKE2#"
      """
      {"publish_schedule": "2099-05-30T10:00:00+00:00"}
      """
      Then we get error 400
      """
      {"_issues": {"validator exception": "400: Takes cannot be scheduled."}, "_status": "ERR"}
      """

    @auth @vocabulary
    Scenario: Correct a Take so that body is from corrected take and other metadata is from last published take
      Given the "validators"
      """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
         {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
         {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports", "members": [{"user": "#CONTEXT_USER_ID#"}]}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
      }
      """
      And we post to "/subscribers" with success
      """
      [{
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }, {
        "name":"Channel 4","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }]
      """
      And we post to "archive" with success
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "Take-1 soccer headline",
          "abstract": "Take-1 abstract",
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "body_html": "Take-1",
          "state": "draft",
          "slugline": "Take-1 slugline",
          "urgency": "4",
          "pubstatus": "usable",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "anpa_category": [{"qcode": "A", "name": "Sport"}],
          "anpa_take_key": "Take"
      }]
      """
      And we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE2"
      """
      {
          "type": "text",
          "headline": "Take-1 soccer headline",
          "slugline": "Take-1 slugline",
          "anpa_take_key": "Take=2",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we patch "/archive/#TAKE2#"
      """
      {"body_html": "Take-2", "abstract": "Take-2 Abstract",
      "headline": "Take-2 soccer headline", "slugline": "Take-2 slugline"}
      """
      And we post to "/archive/#TAKE2#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we get "/archive"
      Then we get list with 3 items
      When we post to "archive/#TAKE2#/link"
      """
      [{}]
      """
      Then we get next take as "TAKE3"
      """
      {
          "type": "text",
          "headline": "Take-2 soccer headline",
          "slugline": "Take-2 slugline",
          "anpa_take_key": "Take=3",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we patch "/archive/#TAKE3#"
      """
      {"body_html": "Take-3", "abstract": "Take-3 Abstract",
      "headline": "Take-3 soccer headline", "slugline": "Take-3 slugline"}
      """
      And we post to "/archive/#TAKE3#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we get "/archive"
      Then we get list with 4 items
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we publish "#TAKE2#" with "publish" type and "published" state
      Then we get OK response
      When we publish "#TAKE3#" with "publish" type and "published" state
      Then we get OK response
      When we get "/published"
      Then we get list with 6 items
      """
      {
        "_items": [
                {
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 3,
                    "_id": "#archive.123.take_package#",
                    "body_html": "Take-1",
                    "_current_version": 3,
                    "slugline": "Take-1 slugline",
                    "headline": "Take-1 soccer headline",
                    "last_published_version": false
                },
                {
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 3,
                    "_id": "#archive.123.take_package#",
                    "body_html": "Take-1<br>Take-2",
                    "_current_version": 4,
                    "slugline": "Take-2 slugline",
                    "headline": "Take-2 soccer headline",
                    "last_published_version": false
                },
                {
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 3,
                    "_id": "#archive.123.take_package#",
                    "body_html": "Take-1<br>Take-2<br>Take-3",
                    "_current_version": 5,
                    "slugline": "Take-3 slugline",
                    "headline": "Take-3 soccer headline",
                    "last_published_version": true
                }
        ]
      }
      """
      When we publish "#TAKE2#" with "correct" type and "corrected" state
      """
      {
        "body_html": "corrected"
      }
      """
      Then we get OK response
      When we get "/published"
      Then we get list with 8 items
      """
      {
        "_items": [
                {
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 3,
                    "_id": "#archive.123.take_package#",
                    "body_html": "Take-1",
                    "_current_version": 3,
                    "slugline": "Take-1 slugline",
                    "headline": "Take-1 soccer headline",
                    "last_published_version": false
                },
                {
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 3,
                    "_id": "#archive.123.take_package#",
                    "body_html": "Take-1<br>Take-2",
                    "_current_version": 4,
                    "slugline": "Take-2 slugline",
                    "headline": "Take-2 soccer headline",
                    "last_published_version": false
                },
                {
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 3,
                    "_id": "#archive.123.take_package#",
                    "body_html": "Take-1<br>Take-2<br>Take-3",
                    "_current_version": 5,
                    "slugline": "Take-3 slugline",
                    "headline": "Take-3 soccer headline",
                    "last_published_version": false
                },
                {
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 3,
                    "_id": "#archive.123.take_package#",
                    "body_html": "Take-1<br>corrected<br>Take-3",
                    "_current_version": 6,
                    "slugline": "Take-2 slugline",
                    "headline": "Take-2 soccer headline",
                    "last_published_version": true
                }
        ]
      }
      """

    @auth @vocabulary
    Scenario: Publishing of Takes with different metadata should go to at least subscribers that received first take
        Given the "validators"
        """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
         {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
        """
        And "desks"
        """
        [{"name": "Sports", "members": [{"user": "#CONTEXT_USER_ID#"}]}]
        """
        And empty "filter_conditions"
        When we post to "/filter_conditions" with "DomesticSport" and success
        """
        [{"field" : "anpa_category", "name" : "Domestic Sport Content", "value" : "T", "operator" : "in"}]
        """
        Then we get OK response
        When we post to "/filter_conditions" with "OverseasSport" and success
        """
        [{"field" : "anpa_category", "name" : "Overseas Sport Content", "value" : "S", "operator" : "in"}]
        """
        Then we get OK response
        Given empty "content_filters"
        When we post to "/content_filters" with "DomesticSportFilter" and success
        """
        [{"content_filter": [{"expression": {"fc": ["#DomesticSport#"]}}], "name": "domestic-sport"}]
        """
        Then we get OK response
        When we post to "/content_filters" with "OverseasSportFilter" and success
        """
        [{"content_filter": [{"expression": {"fc": ["#OverseasSport#"]}}], "name": "overseas-sport"}]
        """
        Then we get OK response
        When we post to "/products" with success
        """
        {
          "name":"prod-1","codes":"abc,xyz",
          "content_filter" : {
            "filter_type" : "permitting",
            "filter_id" : "#DomesticSportFilter#"
          }
        }
        """
        And we post to "/subscribers" with "DomesticSportSubscriber" and success
        """
        {
          "name":"DomesticSportSubscriber","media_type":"media", "subscriber_type": "digital",
          "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "products": ["#products._id#"],
          "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP",
          "config":{"ip":"144.122.244.55","password":"xyz"}}]
        }
        """
        When we post to "/products" with success
        """
        {
          "name":"prod-2","codes":"abc,xyz",
          "content_filter" : {
            "filter_type" : "permitting",
            "filter_id" : "#OverseasSportFilter#"
          }
        }
        """
        And we post to "/subscribers" with "OverseasSportSubscriber" and success
        """
        {
          "name":"OverseasSportSubscriber","media_type":"media", "subscriber_type": "digital",
          "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "products": ["#products._id#"],
          "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP",
          "config":{"ip":"144.122.244.55","password":"xyz"}}]
        }
        """
        Then we get OK response
        When we post to "archive" with success
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "Domestic Sport headline",
            "abstract": "Take-1 abstract",
            "task": {
                "user": "#CONTEXT_USER_ID#"
            },
            "body_html": "Take-1",
            "state": "draft",
            "slugline": "comics",
            "urgency": "4",
            "pubstatus": "usable",
            "subject":[{"qcode": "17004000", "name": "Statistics"}],
            "anpa_category": [{"qcode": "T", "name": "Domestic Sport"}],
            "anpa_take_key": "Take"
        }]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we post to "archive/123/link"
        """
        [{}]
        """
        Then we get next take as "TAKE2"
        """
        {
            "_id": "#TAKE2#",
            "type": "text",
            "headline": "Domestic Sport headline",
            "slugline": "comics",
            "anpa_take_key": "Take=2",
            "state": "draft",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we patch "/archive/#TAKE2#"
        """
        {"headline": "Overseas Sport headline",
         "body_html": "Take-2",
         "anpa_category": [{"qcode": "S", "name": "Overseas Sport"}]}
        """
        Then we get OK response
        When we post to "/archive/#TAKE2#/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we publish "123" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        When we get "/publish_queue"
        Then we get list with 1 items
        """
        {
        "_items": [
                  {
                      "content_type": "composite",
                      "item_id": "#archive.123.take_package#",
                      "item_version": 2,
                      "headline": "Domestic Sport headline",
                      "state": "pending",
                      "subscriber_id": "#DomesticSportSubscriber#"
                  }
           ]
        }
        """
        When we publish "#TAKE2#" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        When we get "/publish_queue"
        Then we get list with 3 items
        """
        {
        "_items": [
                  {
                      "content_type": "composite",
                      "item_id": "#archive.123.take_package#",
                      "item_version": 2,
                      "headline": "Domestic Sport headline",
                      "state": "pending",
                      "subscriber_id": "#DomesticSportSubscriber#"
                  },
                  {
                      "content_type": "composite",
                      "item_id": "#archive.123.take_package#",
                      "item_version": 3,
                      "headline": "Overseas Sport headline",
                      "state": "pending",
                      "subscriber_id": "#DomesticSportSubscriber#"
                  },
                  {
                      "content_type": "composite",
                      "item_id": "#archive.123.take_package#",
                      "item_version": 3,
                      "headline": "Overseas Sport headline",
                      "state": "pending",
                      "subscriber_id": "#OverseasSportSubscriber#"
                  }
           ]
        }
        """
        When we post to "archive/#TAKE2#/link"
        """
        [{}]
        """
        Then we get next take as "TAKE3"
        """
        {
            "_id": "#TAKE3#",
            "type": "text",
            "headline": "Overseas Sport headline",
            "slugline": "comics",
            "anpa_take_key": "Take (reopens)=3",
            "state": "draft",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we patch "/archive/#TAKE3#"
        """
        {"headline": "International headline",
         "body_html": "Take-3",
         "anpa_category": [{"qcode": "I", "name": "International News"}]}
        """
        Then we get OK response
        When we post to "/archive/#TAKE3#/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we publish "#TAKE3#" with "publish" type and "published" state
        Then we get OK response
        When we enqueue published
        When we get "/publish_queue"
        Then we get list with 5 items
        """
        {
        "_items": [
                  {
                      "content_type": "composite",
                      "item_id": "#archive.123.take_package#",
                      "item_version": 2,
                      "headline": "Domestic Sport headline",
                      "state": "pending",
                      "subscriber_id": "#DomesticSportSubscriber#"
                  },
                  {
                      "content_type": "composite",
                      "item_id": "#archive.123.take_package#",
                      "item_version": 3,
                      "headline": "Overseas Sport headline",
                      "state": "pending",
                      "subscriber_id": "#DomesticSportSubscriber#"
                  },
                  {
                      "content_type": "composite",
                      "item_id": "#archive.123.take_package#",
                      "item_version": 3,
                      "headline": "Overseas Sport headline",
                      "state": "pending",
                      "subscriber_id": "#OverseasSportSubscriber#"
                  },
                  {
                      "content_type": "composite",
                      "item_id": "#archive.123.take_package#",
                      "item_version": 5,
                      "headline": "International headline",
                      "state": "pending",
                      "subscriber_id": "#DomesticSportSubscriber#"
                  },
                  {
                      "content_type": "composite",
                      "item_id": "#archive.123.take_package#",
                      "item_version": 5,
                      "headline": "International headline",
                      "state": "pending",
                      "subscriber_id": "#OverseasSportSubscriber#"
                  }

           ]
        }
        """

  @auth @vocabulary
    Scenario: After correcting a take digital package stays as corrected
      Given the "validators"
      """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
         {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
         {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports", "members": [{"user": "#CONTEXT_USER_ID#"}]}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
      }
      """
      And we post to "/subscribers" with success
      """
      [{
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }, {
        "name":"Channel 4","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }]
      """
      And we post to "archive" with success
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "Take-1 soccer headline",
          "abstract": "Take-1 abstract",
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "body_html": "Take-1",
          "state": "draft",
          "slugline": "Take-1 slugline",
          "urgency": "4",
          "pubstatus": "usable",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "anpa_category": [{"qcode": "A", "name": "Sport"}],
          "anpa_take_key": "Take"
      }]
      """
      And we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE2"
      """
      {
          "type": "text",
          "headline": "Take-1 soccer headline",
          "slugline": "Take-1 slugline",
          "anpa_take_key": "Take=2",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we patch "/archive/#TAKE2#"
      """
      {"body_html": "Take-2", "abstract": "Take-2 Abstract",
      "headline": "Take-2 soccer headline", "slugline": "Take-2 slugline"}
      """
      And we post to "/archive/#TAKE2#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we get "/archive"
      Then we get list with 3 items

      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we publish "123" with "correct" type and "corrected" state
      """
      {
        "body_html": "corrected"
      }
      """

      When we get "/published"
      Then we get list with 4 items
      """
      {
        "_items": [
                {
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 2,
                    "_id": "#archive.123.take_package#",
                    "body_html": "corrected",
                    "_current_version": 3,
                    "slugline": "Take-1 slugline",
                    "headline": "Take-1 soccer headline",
                    "last_published_version": true,
                    "state": "corrected"
                }
        ]
      }
      """
      When we publish "#TAKE2#" with "publish" type and "published" state
      Then we get OK response
      When we get "/published"
      Then we get list with 6 items
      """
      {
        "_items": [
                {
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 2,
                    "_id": "#archive.123.take_package#",
                    "body_html": "Take-1",
                    "_current_version": 2,
                    "slugline": "Take-1 slugline",
                    "headline": "Take-1 soccer headline",
                    "last_published_version": false,
                    "state": "published"
                },
                {
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 2,
                    "_id": "#archive.123.take_package#",
                    "body_html": "corrected",
                    "_current_version": 3,
                    "slugline": "Take-1 slugline",
                    "headline": "Take-1 soccer headline",
                    "last_published_version": false,
                    "state": "corrected"
                },
                {
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 2,
                    "_id": "#archive.123.take_package#",
                    "body_html": "corrected<br>Take-2",
                    "_current_version": 4,
                    "slugline": "Take-2 slugline",
                    "headline": "Take-2 soccer headline",
                    "last_published_version": true,
                    "state": "corrected"
                }
        ]
      }
      """


    @auth @vocabulary
    Scenario: New takes of a correction doesn't carry ed notes
      Given the "validators"
      """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
         {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
         {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports", "members": [{"user": "#CONTEXT_USER_ID#"}]}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
      }
      """
      And we post to "/subscribers" with success
      """
      [{
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }, {
        "name":"Channel 4","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }]
      """
      And we post to "archive" with success
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "Take-1 soccer headline",
          "abstract": "Take-1 abstract",
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "body_html": "Take-1",
          "state": "draft",
          "slugline": "Take-1 slugline",
          "urgency": "4",
          "pubstatus": "usable",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "anpa_category": [{"qcode": "A", "name": "Sport"}],
          "anpa_take_key": "Take"
      }]
      """
      And we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we publish "123" with "correct" type and "corrected" state
      """
      {
        "body_html": "corrected", "ednote": "Corrected blah blah"
      }
      """
      When we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE2"
      """
      {
          "type": "text",
          "headline": "Take-1 soccer headline",
          "slugline": "Take-1 slugline",
          "anpa_take_key": "Take (reopens)=2",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      Then we get no "ednote"

    @auth
    Scenario: Publish the very first take with SMS second does not have SMS
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And empty "ingest"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
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
      And we post to "archive" with success
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "Take-1 headline",
          "abstract": "Take-1 abstract",
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "body_html": "Take-1",
          "state": "draft",
          "slugline": "Take-1 slugline",
          "urgency": "4",
          "pubstatus": "usable",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "anpa_category": [{"qcode": "A", "name": "Sport"}],
          "anpa_take_key": "Take",
          "flags": {"marked_for_sms": true},
          "sms_message": "test"
      }]
      """
      And we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE"
      """
      {
          "type": "text",
          "headline": "Take-1 headline",
          "slugline": "Take-1 slugline",
          "anpa_take_key": "Take=2",
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we patch "/archive/#TAKE#"
      """
      {"body_html": "Take-2"}
      """
      And we post to "/archive/#TAKE#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      And we get "/archive"
      Then we get list with 3 items
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we publish "#TAKE#" with "publish" type and "published" state
      Then we get OK response
      When we get "/published"
      Then we get existing resource
      """
      {
          "_items": [
          {
              "flags" : {
                  "marked_for_sms" : true
              },
              "type" : "composite",
              "_current_version" : 2
          },
          {
              "flags" : {
                  "marked_for_sms" : true
              },
              "type" : "text",
              "_current_version" : 3
          },
          {
              "flags" : {
                  "marked_for_sms" : false
              },
              "type" : "composite",
              "_current_version" : 3
          },
          {
              "flags" : {
                  "marked_for_sms" : false
              },
              "type" : "text",
              "_current_version" : 4
          }
          ]
      }
      """

    @auth
    Scenario: Publish takes with associations.
      Given the "validators"
      """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And empty "ingest"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      When we post to "archive"
      """
      [{
          "guid": "123",
          "type": "text",
          "headline": "test1",
          "slugline": "comics",
          "anpa_take_key": "Take",
          "state": "draft",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "task": {
              "user": "#CONTEXT_USER_ID#"
          },
          "body_html": "Take-1"
      }]
      """
      Then we get OK response
      When we post to "/archive/123/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we patch "/archive/123"
      """
      {
        "associations": {
          "featuremedia": {
            "_id": "234",
            "guid": "234",
            "type": "picture",
            "headline": "s234",
            "slugline": "s234",
            "state": "in_progress"
          }
        }
      }
      """
      Then we get OK response
      When we post to "archive/123/link"
      """
      [{}]
      """
      Then we get next take as "TAKE"
      """
      {
          "type": "text",
          "headline": "test1",
          "slugline": "comics",
          "anpa_take_key": "Take=2",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we get "/archive/#TAKE_PACKAGE#"
      Then we get existing resource
      """
      {
        "type": "composite", "package_type": "takes",
        "sequence": 2, "associated_take_sequence": 1,
        "state": "published",
        "_current_version": 2,
        "associations": {
          "featuremedia": {
            "_id": "234",
            "guid": "234",
            "type": "picture",
            "headline": "s234",
            "slugline": "s234",
            "state": "in_progress"
          }
        }
      }
      """
      When we patch "/archive/#TAKE#"
      """
      {"body_html": "this is another take"}
      """
      And we post to "/archive/#TAKE#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we publish "#TAKE#" with "publish" type and "published" state
      Then we get OK response
      When we get "/archive/#TAKE_PACKAGE#"
      Then we get existing resource
      """
      {
        "type": "composite", "package_type": "takes",
        "sequence": 2, "associated_take_sequence": 1,
        "state": "published",
        "_current_version": 3,
        "associations": {
          "featuremedia": {
            "_id": "234",
            "guid": "234",
            "type": "picture",
            "headline": "s234",
            "slugline": "s234",
            "state": "in_progress"
          }
        }
      }
      """
      When we post to "archive/#TAKE#/link"
      """
      [{}]
      """
      Then we get next take as "TAKE2"
      """
      {
          "type": "text",
          "headline": "test1",
          "slugline": "comics",
          "anpa_take_key": "Take (reopens)=3",
          "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "state": "draft",
          "original_creator": "#CONTEXT_USER_ID#"
      }
      """
      When we post to "/archive/#TAKE2#/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      And we patch "/archive/#TAKE2#"
      """
      {
        "body_html": "this is another take",
        "associations": {
          "featuremedia": {
            "_id": "456",
            "guid": "456",
            "type": "picture",
            "headline": "s456",
            "slugline": "s456",
            "state": "in_progress"
          }
        }
      }
      """
      Then we get OK response
      When we publish "#TAKE2#" with "publish" type and "published" state
      Then we get OK response
      When we get "/archive/#TAKE_PACKAGE#"
      Then we get existing resource
      """
      {
        "type": "composite", "package_type": "takes",
        "sequence": 3, "associated_take_sequence": 3,
        "state": "published",
        "_current_version": 5,
        "associations": {
          "featuremedia": {
            "_id": "456",
            "guid": "456",
            "type": "picture",
            "headline": "s456",
            "slugline": "s456",
            "state": "in_progress"
          }
        }
      }
      """
      When we publish "#TAKE2#" with "correct" type and "corrected" state
      """
      {"associations": {}, "slugline": "correction"}
      """
      Then we get OK response
      When we get "/archive/#TAKE_PACKAGE#"
      Then we get existing resource
      """
      {
        "type": "composite", "package_type": "takes",
        "sequence": 3, "associated_take_sequence": 3,
        "state": "corrected",
        "_current_version": 6,
        "associations": {}
      }
      """