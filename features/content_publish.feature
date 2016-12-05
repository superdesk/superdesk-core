Feature: Content Publishing

    @auth
    Scenario: Publish a user content
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
      [{"name": "Sports", "content_expiry": 60}]
      """
      When we post to "/archive" with success
      """
      [{"guid": "123", "type": "text", "headline": "test", "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
      """
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 1, "state": "fetched", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
      }
      """
      And we post to "/subscribers" with "digital" and success
      """
      {
        "name":"Channel 1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we post to "/subscribers" with "wire" and success
      """
      {
        "name":"Channel 2","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
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
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 2 items
      """
      {
        "_items": [
          {"state": "pending", "content_type": "composite",
          "subscriber_id": "#digital#", "item_id": "#archive.123.take_package#",
          "item_version": 2, "ingest_provider": "__none__"},
          {"state": "pending", "content_type": "text",
          "subscriber_id": "#wire#", "item_id": "123", "item_version": 2,
          "ingest_provider": "__none__"}
        ]
      }
      """
      When we get "/legal_archive"
      Then we get existing resource
      """
      {"_items" : [
        {"_id": "123", "guid": "123", "headline": "test", "_current_version": 2, "state": "published",
         "task": {"desk": "Sports", "stage": "Incoming Stage", "user": "test_user"},
         "slugline": "test",
         "body_html": "Test Document body", "subject":[{"qcode": "17004000", "name": "Statistics"}]},
        {"headline": "test", "_current_version": 2, "state": "published", "type": "composite",
         "package_type": "takes", "task": {"desk": "Sports", "stage": "Incoming Stage", "user": "test_user"},
         "sequence": 1,
         "slugline": "test",
         "groups" : [
            {
                "id" : "root",
                "refs" : [
                    {
                        "idRef" : "main"
                    }
                ],
                "role" : "grpRole:NEP"
            },
            {
                "id" : "main",
                "refs" : [
                    {
                        "sequence" : 1,
                        "renditions" : {},
                        "type" : "text",
                        "location" : "legal_archive",
                        "slugline" : "test",
                        "itemClass" : "icls:text",
                        "residRef" : "123",
                        "headline" : "test",
                        "guid" : "123",
                        "_current_version" : 2
                    }
                ],
                "role" : "grpRole:main"
            }
         ],
         "body_html": "Test Document body", "subject":[{"qcode": "17004000", "name": "Statistics"}]}
        ]
      }
      """
      When we get "/legal_archive/123?version=all"
      Then we get list with 2 items
      """
      {"_items" : [
        {"_id": "123", "headline": "test", "_current_version": 1, "state": "fetched",
         "task": {"desk": "Sports", "stage": "Incoming Stage", "user": "test_user"}},
        {"_id": "123", "headline": "test", "_current_version": 2, "state": "published",
         "task": {"desk": "Sports", "stage": "Incoming Stage", "user": "test_user"}}
       ]
      }
      """
      When we get "/legal_archive/#archive.123.take_package#?version=all"
      Then we get list with 1 items
      """
      {"_items" : [

        {"_id": "#archive.123.take_package#", "headline": "test", "_current_version": 2,
         "state": "published", "type": "composite", "package_type": "takes",
         "task": {"desk": "Sports", "stage": "Incoming Stage", "user": "test_user"}}
       ]
      }
      """
      When we transmit items
      And run import legal publish queue
      When we enqueue published
      And we get "/legal_publish_queue"
      Then we get list with 2 items
      """
      {
        "_items": [
          {"state": "success", "content_type": "composite",
          "subscriber_id": "Channel 1", "item_id": "#archive.123.take_package#", "item_version": 2},
          {"state": "success", "content_type": "text",
          "subscriber_id": "Channel 2", "item_id": "123", "item_version": 2}
        ]
      }
      """

    @auth
    @provider
    Scenario: Publish a ingested content
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
      [{"name": "Sports", "content_expiry": 60}]
      """
      And empty "ingest"
      When we fetch from "AAP" ingest "aap.xml"
      And we post to "/ingest/#AAP.AAP.115314987.5417374#/fetch"
      """
      {"desk": "#desks._id#"}
      """
      Then we get "_id"
      When we get "/archive/#_id#"
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 1, "state": "fetched", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
      }
      """
      And we post to "/subscribers" with "digital" and success
      """
      {
        "name":"Channel 1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we post to "/subscribers" with "wire" and success
      """
      {
        "name":"Channel 2","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we publish "#_id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 2 items
      """
      {
        "_items": [
          {"state": "pending", "content_type": "text",
          "subscriber_id": "#wire#", "item_id": "#_id#", "item_version": 2,
          "ingest_provider": "#providers.aap#"},
          {"state": "pending", "content_type": "composite",
          "subscriber_id": "#digital#", "item_version": 2,
          "ingest_provider": "__none__"}
        ]
      }
      """

    @auth
    @vocabulary
    Scenario: Publish a user content passes the filter
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
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
        "slugline": "test",
        "body_html": "Test Document body"}]
      """
      Given empty "filter_conditions"
      When we post to "/filter_conditions" with success
      """
      [{"name": "sport", "field": "headline", "operator": "like", "value": "est"}]
      """
      Then we get latest
      Given empty "content_filters"
      When we post to "/content_filters" with success
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
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital",  "email": "test@test.com",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      Then we get latest
      When we publish "#archive._id#" with "publish" type and "published" state
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
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 1 items

    @auth
    @vocabulary
    Scenario: Publish a user content blocked by the filter
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
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
        "slugline": "test",
        "body_html": "Test Document body"}]
      """

      Given empty "filter_conditions"
      When we post to "/filter_conditions" with success
      """
      [{"name": "sport", "field": "headline", "operator": "like", "value": "est"}]
      """

      Then we get latest
      Given empty "content_filters"
      When we post to "/content_filters" with success
      """
      [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer-only"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz",
        "content_filter":{"filter_id":"#content_filters._id#", "filter_type": "blocking"}
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital",  "email": "test@test.com",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """

      Then we get latest
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 0 items

    @auth
    @vocabulary
    Scenario: Publish a user content blocked by global filter
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
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
        "slugline": "test",
        "body_html": "Test Document body"}]
      """

      Given empty "filter_conditions"
      When we post to "/filter_conditions" with success
      """
      [{"name": "sport", "field": "headline", "operator": "like", "value": "est"}]
      """

      Then we get latest
      Given empty "content_filters"
      When we post to "/content_filters" with success
      """
      [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}],
        "name": "soccer-only", "is_global": true}]
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
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital",  "email": "test@test.com",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """

      Then we get latest
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 0 items

    @auth
    @vocabulary
    Scenario: Publish a user content bypassing the global filter
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
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
        "slugline": "test",
        "body_html": "Test Document body"}]
      """

      Given empty "filter_conditions"
      When we post to "/filter_conditions" with success
      """
      [{"name": "sport", "field": "headline", "operator": "like", "value": "est"}]
      """

      Then we get latest
      Given empty "content_filters"
      When we post to "/content_filters" with success
      """
      [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}],
        "name": "soccer-only", "is_global": true}]
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
        "name":"Channel 3",
        "media_type":"media",
        "subscriber_type": "digital",
        "email": "test@test.com",
        "products": ["#products._id#"],
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}],
        "global_filters": {"#content_filters._id#": false}
      }
      """

      Then we get latest
      When we publish "#archive._id#" with "publish" type and "published" state
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
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 1 items

    @auth
    Scenario: Publish user content that fails validation
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{"headline": {"required": true}}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "slugline": "test",
        "body_html": "Test Document body"}]
      """
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get response code 400
      """
        {"_issues": {"validator exception": "Publish failed due to {'headline': 'required field'}"}, "_status": "ERR"}
      """

    @auth
    Scenario: Publish a user content if content format is not compatible
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "type": "image", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "slugline": "test",
        "body_html": "Test Document body"}]
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
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get response code 200

    @auth
    Scenario: Schedule a user content publish
      Given empty "subscribers"
      And "desks"
      """
      [{"name": "Sports", "content_expiry": 60}]
      """
      And the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "publish_schedule":"#DATE+2#",
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
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
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "scheduled", "operation": "publish"}
      """
      And we get expiry for schedule and embargo content 60 minutes after "#archive_publish.publish_schedule#"
      When we get "/published"
      Then we get list with 2 items
      """
      {
        "_items": [
          {
            "_id": "123", "type": "text", "state": "scheduled",
            "_current_version": 2, "operation": "publish", "queue_state": "pending"
          },
          {
            "_id": "#archive.123.take_package#", "type": "composite",
            "state": "scheduled", "_current_version": 2, "operation": "publish",
            "queue_state": "pending"
          }
        ]
      }
      """
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 0 items
      When we get "/legal_archive/123"
      Then we get error 404
      When the publish schedule lapses
      """
      ["123", "#archive.123.take_package#"]
      """
      When we enqueue published
      And we get "/published"
      Then we get list with 2 items
      """
      {
        "_items": [
          {
            "_id": "123", "type": "text", "state": "published",
            "_current_version": 3, "operation": "publish", "queue_state": "queued_not_transmitted"
          },
          {
            "_id": "#archive.123.take_package#", "type": "composite",
            "state": "published", "_current_version": 3, "operation": "publish",
            "queue_state": "queued"
          }
        ]
      }
      """
      When we get "/publish_queue"
      Then we get list with 1 items
      When we transmit items
      And run import legal publish queue
      When we get "/legal_archive/123"
      Then we get OK response
      And we get existing resource
      """
          {
            "_id": "123", "type": "text", "state": "published", "_current_version": 3
          }
      """
      When we get "/legal_archive/#archive.123.take_package#"
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "published", "type": "composite", "task":{"desk": "#desks.name#"}}
      """
      When we expire items
      """
      ["123", "#archive.123.take_package#"]
      """
      And we get "/published"
      Then we get list with 0 items
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 0 items
      When we get "/archived"
      Then we get list with 2 items
      """
      {"_items" : [
        {"package_type": "takes", "item_id": "#archive.123.take_package#",
         "state": "published", "type": "composite", "_current_version": 3},
        {"item_id": "123", "state": "published", "type": "text", "_current_version": 3}
        ]
      }
      """

    @auth
    Scenario: Schedule a user content publish with different time zone
      Given empty "subscribers"
      And "desks"
      """
      [{"name": "Sports", "content_expiry": 60}]
      """
      And the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
      """
      When we patch "/archive/123"
      """
      {
        "publish_schedule":"2020-02-13T22:46:19.000Z",
        "schedule_settings": {"time_zone": "Australia/Sydney"}
      }
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
      When we get "/archive"
      Then we get list with 1 items
      """
      {
        "_items":
          [
            {"publish_schedule":  "2020-02-13T22:46:19+0000",
             "schedule_settings":  {"utc_publish_schedule": "2020-02-13T11:46:19+0000"}
            }
          ]
      }
      """
      When we patch "/archive/123"
      """
      {"publish_schedule":  "2020-03-13T22:46:19+0000"}
      """
      Then we get response code 200
      When we get "/archive/123"
      Then we get existing resource
      """
      {"publish_schedule":  "2020-03-13T22:46:19+0000",
       "schedule_settings":  {"utc_publish_schedule": "2020-03-13T11:46:19+0000"}
      }
      """
      When we patch "/archive/123"
      """
      {"schedule_settings":  {"time_zone": null}}
      """
      Then we get response code 200
      When we get "/archive/123"
      Then we get existing resource
      """
      {"publish_schedule":  "2020-03-13T22:46:19+0000",
       "schedule_settings":  {"utc_publish_schedule": "2020-03-13T22:46:19+0000"}
      }
      """
      When we patch "/archive/123"
      """
      {"publish_schedule":  null}
      """
      Then we get response code 200
      When we get "/archive/123"
      Then we get existing resource
      """
      {"publish_schedule":  null,
       "schedule_settings":  {"utc_publish_schedule": null}
      }
      """


    @auth
    Scenario: Deschedule an item
      Given empty "subscribers"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "publish_schedule": "#DATE+1#",
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
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
        "name":"Digital","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      },
      {
        "name":"Wire","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      ]
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "scheduled"}
      """
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 0 items
      When we patch "/archive/123"
      """
      {"publish_schedule": null}
      """
      And we get "/archive"
      Then we get existing resource
      """
      {
          "_items": [
              {
                  "_current_version": 3,
                  "state": "in_progress",
                  "type": "text",
                  "_id": "123"

              }
          ]
      }
      """
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 0 items
      When we get "/published"
      Then we get list with 0 items

    @auth
    Scenario: Deschedule an item fails if date is past
      Given empty "subscribers"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "slugline": "test",
        "body_html": "Test Document body"}]
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
      And we patch "/archive/123"
      """
      {"publish_schedule": "2010-05-30T10:00:00+00:00"}
      """
      Then we get response code 400

    @auth
    Scenario: Publish a user content and stays on the same stage
      Given "desks"
      """
      [{"name": "Sports"}]
      """
      And the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
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
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """

    @auth
    Scenario: Clean autosave on publishing item
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
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
      And we post to "/archive_autosave"
      """
      {"_id": "#archive._id#", "guid": "123", "headline": "testing", "state": "fetched"}
      """
      Then we get existing resource
      """
      {"_id": "#archive._id#", "guid": "123", "headline": "testing", "_current_version": 1, "state": "fetched",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
      """
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we get "/archive_autosave/#archive._id#"
      Then we get error 404

    @auth
    Scenario: We can lock a published content and then kill it
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
      {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 0, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
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
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we post to "/archive/#archive._id#/lock"
      """
      {}
      """
      Then we get OK response
      When we publish "#archive._id#" with "kill" type and "killed" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "killed", "operation": "kill", "pubstatus": "canceled", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}, "version_creator": "#CONTEXT_USER_ID#"}
      """
      When we post to "/archive/#archive._id#/unlock"
      """
      {}
      """
      Then we get OK response

    @auth
    Scenario: We can lock a published content and then correct it
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
      {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 0, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
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
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we enqueue published
      When we get "/legal_archive/123"
      Then we get OK response
      When we get "/legal_archive/123?version=all"
      Then we get OK response
      When we get "/legal_archive/#archive.123.take_package#"
      Then we get OK response
      When we transmit items
      And run import legal publish queue
      And we get "/legal_publish_queue"
      Then we get list with 1 items
      When we post to "/archive/#archive._id#/lock"
      """
      {}
      """
      Then we get OK response
      When we get "/workqueue?source={"filter": {"term": {"lock_user": "#CONTEXT_USER_ID#"}}}"
      Then we get list with 1 items
      """
      {"_items": [{"guid": "123", "headline": "test", "state": "published",
                   "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
                   "subject":[{"qcode": "17004000", "name": "Statistics"}],
                    "slugline": "test", "body_html": "Test Document body"}]}
      """
      When we publish "#archive._id#" with "correct" type and "corrected" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "corrected", "operation": "correct", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we enqueue published
      When we post to "/archive/#archive._id#/unlock"
      """
      {}
      """
      Then we get OK response
      When we get "/legal_archive/123"
      Then we get OK response
      When we get "/legal_archive/123?version=all"
      Then we get OK response
      When we get "/legal_archive/#archive.123.take_package#"
      Then we get OK response
      When we transmit items
      And run import legal publish queue
      And we get "/legal_publish_queue"
      Then we get list with 2 items

    @auth
    Scenario: We can lock a published content and then correct it and then kill the article
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
      {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
      {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
      """
      When we post to "/archive" with success
      """
      [{"guid": "123", "headline": "test", "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
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
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we enqueue published
      When we get "/legal_archive/123"
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "published"}
      """
      When we get "/legal_archive/123?version=all"
      Then we get list with 2 items
      """
      {
        "_items":[
          {"_current_version": 1, "state": "fetched"},
          {"_current_version": 2, "state": "published"}
        ]
      }
      """
      When we transmit items
      And run import legal publish queue
      And we get "/legal_publish_queue"
      Then we get list with 1 items
      """
      {
        "_items":[
          {"item_version": 2, "publishing_action": "published", "item_id": "123"}
        ]
      }
      """
      When we post to "/archive/#archive._id#/lock"
      """
      {}
      """
      Then we get OK response
      When we publish "#archive._id#" with "correct" type and "corrected" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "corrected", "operation": "correct", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      And we get updated timestamp "versioncreated"
      When we enqueue published
      When we post to "/archive/#archive._id#/unlock"
      """
      {}
      """
      Then we get OK response
      When we get "/legal_archive/123"
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "corrected"}
      """
      When we get "/legal_archive/123?version=all"
      Then we get list with 3 items
      """
      {
        "_items":[
          {"_current_version": 1, "state": "fetched"},
          {"_current_version": 2, "state": "published"},
          {"_current_version": 3, "state": "corrected"}
        ]
      }
      """
      When we transmit items
      And run import legal publish queue
      And we get "/legal_publish_queue"
      Then we get list with 2 items
      """
      {
        "_items":[
          {"item_version": 2, "publishing_action": "published", "item_id": "123"},
          {"item_version": 3, "publishing_action": "corrected", "item_id": "123"}
        ]
      }
      """
      When we post to "/archive/#archive._id#/lock"
      """
      {}
      """
      Then we get OK response
      When we publish "#archive._id#" with "kill" type and "killed" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 4, "state": "killed", "operation": "kill", "pubstatus": "canceled", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      And we get updated timestamp "versioncreated"
      When we enqueue published
      When we post to "/archive/#archive._id#/unlock"
      """
      {}
      """
      Then we get OK response
      When we get "/legal_archive/123"
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 4, "state": "killed"}
      """
      When we get "/legal_archive/123?version=all"
      Then we get list with 4 items
      """
      {
        "_items":[
          {"_current_version": 1, "state": "fetched"},
          {"_current_version": 2, "state": "published"},
          {"_current_version": 3, "state": "corrected"},
          {"_current_version": 4, "state": "killed"}
        ]
      }
      """
      When we transmit items
      And run import legal publish queue
      And we get "/legal_publish_queue"
      Then we get list with 3 items
      """
      {
        "_items":[
          {"item_version": 2, "publishing_action": "published", "item_id": "123"},
          {"item_version": 3, "publishing_action": "corrected", "item_id": "123"},
          {"item_version": 4, "publishing_action": "killed", "item_id": "123"}
        ]
      }
      """

    @auth
    Scenario: Publishing an already corrected published story fails
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
      {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
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
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we post to "/archive/#archive._id#/lock"
      """
      {}
      """
      Then we get OK response
      When we publish "#archive._id#" with "correct" type and "corrected" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "corrected", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get response code 400

    @auth
    Scenario: We can correct a corrected story
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
      {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
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
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we post to "/archive/#archive._id#/lock"
      """
      {}
      """
      Then we get OK response
      When we publish "#archive._id#" with "correct" type and "corrected" state
      """
      {"headline": "test-1"}
      """
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "corrected", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we publish "#archive._id#" with "correct" type and "corrected" state
      """
      {"headline": "test-2"}
      """
      Then we get OK response
      When we get "/published"
      Then we get existing resource
      """
      {
          "_items": [
              {
                  "headline": "test",
                  "_current_version": 2,
                  "state": "published"
              },
              {
                  "headline": "test-1",
                  "_current_version": 3,
                  "state": "corrected"
              },
              {
                  "headline": "test-2",
                  "_current_version": 4,
                  "state": "corrected"
              }
          ]
      }
      """

    @auth
    Scenario: User can't publish without a privilege
      Given "archive"
      """
      [{"headline": "test", "_current_version": 1, "state": "fetched"}]
      """
      And we login as user "foo" with password "bar" and user type "user"
      """
      {"user_type": "user", "email": "foo.bar@foobar.org"}
      """
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get response code 403

    @auth
    Scenario: User can't publish a draft item
      Given "archive"
      """
      [{"headline": "test", "_current_version": 1, "state": "draft"}]
      """
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get response code 400

    @auth
    Scenario: User can't update a published item
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
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
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we patch "/archive/#archive._id#"
      """
      {"headline": "updating a published item"}
      """
      Then we get response code 400

    @auth
    Scenario: As a user I shouldn't be able to publish an item which is marked as not for publication
      Given "desks"
      """
      [{"name": "Sports"}]
      """
      When we post to "/archive" with success
      """
      [{"guid": "123", "headline": "test",
        "body_html": "body", "state": "fetched",
        "slugline": "test",
        "flags": {"marked_for_not_publication": true},
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get error 400
      """
      {"_issues": {"validator exception": "400: Cannot publish an item which is marked as Not for Publication"}}
      """

    @auth
    Scenario: Assign a default Source to user created content Items and is overwritten by Source at desk level when published
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports", "source": "Superdesk Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test",
        "body_html": "body", "_current_version": 1, "state": "fetched",
        "slugline": "test",
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
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
      And we post to "/stages" with success
      """
      [{"name": "Published Stage", "task_status": "done", "desk": "#desks._id#"}]
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "source": "Superdesk Sports", "state": "published", "task":{"desk": "#desks._id#"}}
      """

    @auth
    Scenario: Publish can't publish the same headline to SMS twice
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
            "schema": {},
            "type": "composite",
            "act": "publish",
            "_id": "publish_composite"
        }
      ]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "122", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"},
        {"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
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
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10},
        "email": "test@test.com", "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "AAP SMS", "delivery_type":"ODBC","config":{}}]
      }
      """

      And we publish "122" with "publish" type and "published" state
      Then we get OK response
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 0 items

    @auth
    Scenario: Publish fails when publish validators fail
      Given the "validators"
      """
        [{"_id": "publish_text", "type": "text", "act": "publish", "schema": {
              "dateline": {
                  "type": "dict",
                  "required": true,
                  "schema": {
                      "located": {"type": "dict", "required": true},
                      "date": {"type": "datetime", "required": true},
                      "source": {"type": "string", "required": true},
                      "text": {"type": "string", "required": true}
                  }
              }
            }
        }]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "dateline": {},
        "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body"}]
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
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get error 400
      """
      {"_issues": {"validator exception": "[['DATELINE is a required field']]"}, "_status": "ERR"}
      """

    @auth
    Scenario: Sign Off is updated when published and corrected but not when killed
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
      When we post to "/archive" with success
      """
      [{"guid": "123", "type": "text", "headline": "test", "state": "fetched",
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
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
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get existing resource
      """
      {"_current_version": 2, "state": "published", "sign_off": "abc", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we switch user
      And we publish "#archive._id#" with "correct" type and "corrected" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "corrected", "sign_off": "abc/foo", "operation": "correct", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we login as user "bar" with password "foobar" and user type "admin"
      """
      {"sign_off": "bar"}
      """
      And we publish "#archive._id#" with "kill" type and "killed" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 4, "state": "killed", "pubstatus": "canceled", "sign_off": "abc/foo", "operation": "kill", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """

    @auth @vocabulary
    Scenario: Publish broadcast content to wire/digital subscribers
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
              "schema": {},
              "type": "text",
              "act": "correct",
              "_id": "correct_text"
          }
        ]
      """
      And "desks"
      """
      [{"name": "Sports", "members": [{"user": "#CONTEXT_USER_ID#"}]}]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
      }
      """
      And we post to "/subscribers" with "DigitalSubscriber" and success
      """
      {
        "name":"Digital","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we post to "/subscribers" with "WireSubscriber" and success
      """
      {
        "name":"Wire","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we post to "/archive/123/broadcast"
      """
      [{"desk": "#desks._id#"}]
      """
      Then we get OK response
      When we patch "/archive/#broadcast._id#"
      """
      {
        "headline": "broadcast content",
        "body_html": "broadcast content"
      }
      """
      When we publish "#broadcast._id#" with "publish" type and "published" state
      Then we get OK response
      When we get "/archive/#broadcast._id#"
      Then we get existing resource
      """
      { "_current_version": 3,
        "state": "published",
        "task":{"desk": "#desks._id#", "stage": "#desks.working_stage#"},
        "_id": "#broadcast._id#",
        "genre": [{"name": "Broadcast Script", "qcode": "Broadcast Script"}],
        "broadcast": {
            "master_id": "123"
          }
       }
      """
      When we get "/published"
      Then we get existing resource
      """
      {
        "_items" : [
            {
              "_current_version": 3,
              "state": "published",
              "task":{"desk": "#desks._id#", "stage": "#desks.working_stage#"},
              "_id": "#broadcast._id#",
              "genre": [{"name": "Broadcast Script", "qcode": "Broadcast Script"}],
              "broadcast": {
                  "master_id": "123"
              }
            }
        ]
      }
      """
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 4 items
      """
      {
        "_items": [
          {
            "item_version": 3,
            "publishing_action": "published",
            "headline": "broadcast content",
            "item_id": "#broadcast._id#",
            "subscriber_id": "#WireSubscriber#"
          },
          {
            "item_version": 3,
            "publishing_action": "published",
            "headline": "broadcast content",
            "item_id": "#broadcast._id#",
            "subscriber_id": "#DigitalSubscriber#"
          }
        ]
      }
      """

    @auth
    Scenario: Save and publish a text item with body text
      Given the "validators"
      """
        [
        {
            "schema": {
              "body_html": {
              "type": "string",
              "required": true,
              "nullable": false,
              "empty": false}
            },
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {
              "body_html": {
              "type": "string",
              "required": true,
              "nullable": false,
              "empty": false
              }
            }
        }
        ]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline":
        "test", "_current_version": 1,
        "slugline": "test",
        "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}]}]
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
      And we publish "#archive._id#" with "publish" type and "published" state
      """
      {"body_html": "Test Document body"}
      """
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

    @auth
    Scenario: User should be able to create a new take after the publish schedule passes
      Given "products"
      """
      [{
        "_id": "1", "name":"prod-1", "codes":"abc,xyz"
      }]
      """
      And "subscribers"
      """
      [{"name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
       "products": ["1"],
       "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }]
      """
      And "desks"
      """
      [{"name": "Sports", "content_expiry": 60, "members": [{"user": "#CONTEXT_USER_ID#"}]}]
      """
      And the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "publish_schedule":"#DATE+1#", "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test", "body_html": "Test Document body"}]
      """
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "scheduled", "operation": "publish"}
      """
      When we get "/published"
      Then we get list with 2 items
      When the publish schedule lapses
      """
      ["123", "#archive.123.take_package#"]
      """
      When we enqueue published
      And we get "/published"
      Then we get list with 2 items
      """
      {
        "_items": [
          {
            "_id": "123", "type": "text", "state": "published"
          },
          {
            "_id": "#archive.123.take_package#", "type": "composite", "state": "published"
          }
        ]
      }
      """
      When we get "/publish_queue"
      Then we get list with 1 items
      When we post to "/archive/123/link"
      """
      [{"desk": "#desks._id#"}]
      """
      Then we get OK response
      When we get takes package "/archive/123" and validate
      """
      {"type": "composite", "package_type": "takes",
       "groups" : [{"refs" : [{"guid" : "123", "sequence" : 1}, {"sequence" : 2}],
                    "role" : "grpRole:main", "id" : "main"}]
      }
      """


    @auth
    Scenario: Publish item with custom subject fields
      Given the "content_types"
      """
        [
            {
                "_id": "Standard",
                "label": "Standard",
                "priority": 80,
                "enabled": true,
                "schema": {
                    "slugline": {"type": "string", "required": true, "maxlength": 64, "minlength": 1},
                    "subject": {
                      "type": "list",
                      "mandatory_in_list": {"scheme": {"subject": "subject_custom", "category": "category"}},
                      "schema": {
                         "type": "dict",
                         "schema": {
                            "name": {},
                            "qcode": {},
                            "scheme": {
                               "type": "string",
                               "required": true,
                               "allowed": ["subject_custom", "category"]
                            },
                            "service": {},
                            "parent": {}
                          }
                      }
                    }
                },
                "editor": {
                    "slugline": {"order": 1},
                    "category": {"order": 2, "sdWidth": "half", "required": true},
                    "subject_custom": {"order": 3, "sdWidth": "full", "required": true}
                }
            }
        ]
      """
      And "desks"
      """
      [{"name": "Sports", "content_expiry": 60}]
      """
      When we post to "/archive" with success
      """
      [{"guid": "123", "type": "text", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject": [{"name": "DiDFødselsdag", "qcode": "DiDFødselsdag", "scheme": "category", "service": {"d": 1, "i": 1}},
                    {"name": "arkeologi", "qcode": "01001000", "scheme": "subject_custom", "parent": "01000000"}],
        "slugline": "test", "state": "fetched", "profile": "Standard"}]
      """
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 1, "state": "fetched", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """


    @auth
    Scenario: Fail on category when publish item with custom subject fields
      Given the "content_types"
      """
        [
            {
                "_id": "Standard",
                "label": "Standard",
                "priority": 80,
                "enabled": true,
                "schema": {
                    "slugline": {"type": "string", "required": true, "maxlength": 64, "minlength": 1},
                    "subject": {
                      "type": "list",
                      "mandatory_in_list": {"scheme": {"subject": "subject_custom", "category": "category"}},
                      "schema": {
                         "type": "dict",
                         "schema": {
                            "name": {},
                            "qcode": {},
                            "scheme": {
                               "type": "string",
                               "required": true,
                               "allowed": ["subject_custom", "category"]
                            },
                            "service": {},
                            "parent": {}
                          }
                      }
                    }
                },
                "editor": {
                    "slugline": {"order": 1},
                    "category": {"order": 2, "sdWidth": "half", "required": true},
                    "subject_custom": {"order": 3, "sdWidth": "full", "required": true}
                }
            }
        ]
      """
      And "desks"
      """
      [{"name": "Sports", "content_expiry": 60}]
      """
      When we post to "/archive" with success
      """
      [{"guid": "123", "type": "text", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject": [{"name": "arkeologi", "qcode": "01001000", "scheme": "subject_custom", "parent": "01000000"}],
        "slugline": "test", "state": "fetched", "profile": "Standard"}]
      """
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 1, "state": "fetched", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get error 400
      """
        {"_issues": {"validator exception": "[['CATEGORY is a required field']]"}}
      """


    @auth
    Scenario: Fail on subject when publish item with custom subject fields
      Given the "content_types"
      """
        [
            {
                "_id": "Standard",
                "label": "Standard",
                "priority": 80,
                "enabled": true,
                "schema": {
                    "slugline": {"type": "string", "required": true, "maxlength": 64, "minlength": 1},
                    "subject": {
                      "type": "list",
                      "mandatory_in_list": {"scheme": {"subject": "subject_custom", "category": "category"}},
                      "schema": {
                         "type": "dict",
                         "schema": {
                            "name": {},
                            "qcode": {},
                            "scheme": {
                               "type": "string",
                               "required": true,
                               "allowed": ["subject_custom", "category"]
                            },
                            "service": {},
                            "parent": {}
                          }
                      }
                    }
                },
                "editor": {
                    "slugline": {"order": 1},
                    "category": {"order": 2, "sdWidth": "half", "required": true},
                    "subject_custom": {"order": 3, "sdWidth": "full", "required": true}
                }
            }
        ]
      """
      And "desks"
      """
      [{"name": "Sports", "content_expiry": 60}]
      """
      When we post to "/archive" with success
      """
      [{"guid": "123", "type": "text", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject": [{"name": "DiDFødselsdag", "qcode": "DiDFødselsdag", "scheme": "category", "service": {"d": 1, "i": 1}}],
        "slugline": "test", "state": "fetched", "profile": "Standard"}]
      """
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 1, "state": "fetched", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get error 400
      """
        {"_issues": {"validator exception": "[['SUBJECT is a required field']]"}}
      """

    @auth
    Scenario: Publish fails when publish validators fail for embedded item
      Given the "validators"
      """
        [{"_id": "publish_embedded", "type": "picture", "act": "publish", "embedded": true,
          "schema": {"headline": {"type": "string","required": true}}},
         {"_id": "publish_text", "type": "text", "act": "publish", "schema": {}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "in_progress",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body",
        "associations": {"featureimage": {"_id": "234", "guid": "234", "type": "picture", "slugline": "s234", "state": "in_progress"}}}]
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
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get error 400
      """
      {"_issues": {"validator exception": "['Associated item s234 234: HEADLINE is a required field']"}, "_status": "ERR"}
      """

    @auth
    Scenario: PUBLISHED_CONTENT_EXPIRY_MINUTES setting overrides content expiry setting.
      Given the "validators"
      """
        [{"_id": "publish_embedded", "type": "picture", "act": "publish", "embedded": true,
          "schema": {"headline": {"type": "string","required": true}}},
         {"_id": "publish_text", "type": "text", "act": "publish", "schema": {}}]
      """
      And "desks"
      """
      [{"name": "Sports", "content_expiry": 180}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
      }
      """
      And we post to "/subscribers" with "digital" and success
      """
      {
        "name":"Channel 1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we post to "/subscribers" with "wire" and success
      """
      {
        "name":"Channel 2","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      When we post to "/archive" with success
      """
      [{"guid": "123", "type": "text", "headline": "test", "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
      """
      Then we get OK response
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we get "/archive/123"
      Then we get OK response
      And we get content expiry 180
      When we get "/archive/#archive.123.take_package#"
      Then we get OK response
      And we get content expiry 180
      And we set published item expiry 60
      When we post to "/archive" with success
      """
      [{"guid": "456", "type": "text", "headline": "test", "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
      """
      Then we get OK response
      And we get content expiry 180
      When we publish "456" with "publish" type and "published" state
      Then we get OK response
      When we get "/archive/456"
      Then we get OK response
      And we get content expiry 60
      When we get "/archive/#archive.456.take_package#"
      Then we get OK response
      And we get content expiry 60
      When we get "/published/123"
      Then we get OK response
      And we get content expiry 180
      When we get "/published/#archive.123.take_package#"
      Then we get OK response
      And we get content expiry 180
      When we get "/published/456"
      Then we get OK response
      And we get content expiry 60
      When we get "/published/#archive.456.take_package#"
      Then we get OK response
      And we get content expiry 60
