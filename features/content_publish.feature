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
        "body_html": "Test Document body",
        "dateline": {
          "located" : {
              "country" : "Afghanistan",
              "tz" : "Asia/Kabul",
              "city" : "Mazar-e Sharif",
              "alt_name" : "",
              "country_code" : "AF",
              "city_code" : "Mazar-e Sharif",
              "dateline" : "city",
              "state" : "Balkh",
              "state_code" : "AF.30"
          },
          "text" : "MAZAR-E SHARIF, Dec 30  -",
          "source": "AAP"}
        }]
      """
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 1, "state": "fetched", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we patch "/users/#CONTEXT_USER_ID#"
      """
      {"byline": "Admin Admin"}
      """
      Then we get OK response
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
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
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}],
        "api_products": ["#products._id#"]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {
        "_current_version": 2,
        "type": "text",
        "state": "published",
        "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}
       }
      """
      And we get "byline" does not exist
      When we get "/published"
      Then we get existing resource
      """
      {"_items" : [
        {"_id": "123", "guid": "123", "headline": "test", "_current_version": 2, "state": "published",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "lock_user": "__none__"
        }]}
      """
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 3 items
      """
      {
        "_items": [
          {"state": "pending", "content_type": "text",
          "subscriber_id": "#digital#", "item_id": "123",
          "item_version": 2, "ingest_provider": "__none__",
          "destination": {
            "delivery_type": "email"
          }},
          {"state": "pending", "content_type": "text",
          "subscriber_id": "#wire#", "item_id": "123", "item_version": 2,
          "ingest_provider": "__none__",
          "destination": {
            "delivery_type": "email"
          }},
          {"state": "success", "content_type": "text",
          "subscriber_id": "#wire#", "item_id": "123",
          "item_version": 2, "ingest_provider": "__none__",
          "destination": {
            "delivery_type": "content_api"
          }}
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
      When we transmit items
      And run import legal publish queue
      When we enqueue published
      And we get "/legal_publish_queue"
      Then we get list with 3 items
      """
      {
        "_items": [
          {"state": "success", "content_type": "text",
          "subscriber_id": "Channel 1", "item_id": "123", "item_version": 2},
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
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
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
          {"state": "pending", "content_type": "text", "destination": {"delivery_type": "email"},
          "subscriber_id": "#wire#", "item_id": "#_id#", "item_version": 2,
          "ingest_provider": "#providers.aap#"},
          {"state": "pending", "content_type": "text", "destination": {"delivery_type": "email"},
          "subscriber_id": "#digital#", "item_version": 2, "item_id": "#_id#",
          "ingest_provider": "#providers.aap#"}
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
          "content_filter":{"filter_id":"#content_filters._id#", "filter_type": "permitting"}, "product_type": "both"
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
    Scenario: Publish a user content that use API product
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
      [{"guid": "123", "type": "text", "headline": "publish via direct", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "anpa_category": [{"qcode": "a", "name": "National"}],
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"},
       {"guid": "456", "type": "text", "headline": "publish via api", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "anpa_category": [{"qcode": "a", "name": "National"}],
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
      """
      Given empty "filter_conditions"
      When we post to "/filter_conditions" with "fc_direct" and success
      """
      [{"name": "fc_direct", "field": "headline", "operator": "like", "value": "direct"}]
      """
      And we post to "/filter_conditions" with "fc_api" and success
      """
      [{"name": "fc_api", "field": "headline", "operator": "like", "value": "api"}]
      """
      Then we get latest
      Given empty "content_filters"
      When we post to "/content_filters" with "cf_direct" and success
      """
      [{"content_filter": [{"expression": {"fc": ["#fc_direct#"]}}], "name": "cf_direct"}]
      """
      And we post to "/content_filters" with "cf_api" and success
      """
      [{"content_filter": [{"expression": {"fc": ["#fc_api#"]}}], "name": "cf_api"}]
      """
      And we post to "/products" with "p_direct" and success
        """
        [{
          "name":"prod-1","codes":"direct",
          "content_filter":{"filter_id":"#cf_direct#", "filter_type": "permitting"},
          "product_type": "direct"
        }]
        """
      And we post to "/products" with "p_api" and success
        """
        [{
          "name":"prod-2","codes":"api",
          "content_filter":{"filter_id":"#cf_api#", "filter_type": "permitting"},
          "product_type": "api"
        }]
        """
      And we post to "/subscribers" with "sub_direct" and success
      """
      {
        "name":"Channel Direct","media_type":"media", "subscriber_type": "wire",  "email": "test@test.com",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "products": ["#p_direct#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we post to "/subscribers" with "sub_api" and success
      """
      {
        "name":"Channel API","media_type":"media", "subscriber_type": "wire",  "email": "test@test.com",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "api_products": ["#p_api#"]
      }
      """
      Then we get latest
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we get "/published"
      Then we get list with 1 items
      """
      {"_items" : [
        {"_id": "123", "headline": "publish via direct", "_current_version": 2, "state": "published",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
      ]}
      """
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 1 items
      """
      {"_items" : [
        {"item_id": "123", "headline": "publish via direct",
        "destination": {"format": "nitf", "delivery_type":"email"},
        "item_version": 2, "content_type": "text", "state": "pending", "publishing_action": "published"}
      ]}
      """
      When we get "/items/123"
      Then we get OK response
      Then we assert the content api item "123" is not published to any subscribers
      When we publish "456" with "publish" type and "published" state
      Then we get OK response
      When we get "/published"
      Then we get list with 2 items
      """
      {"_items" : [
        {"_id": "123", "headline": "publish via direct", "_current_version": 2, "state": "published",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}},
        {"_id": "456", "headline": "publish via api", "_current_version": 2, "state": "published",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
      ]}
      """
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 2 items
      """
      {"_items" : [
        {"item_id": "123", "headline": "publish via direct", "subscriber_id": "#sub_direct#",
        "destination": {"format": "nitf", "delivery_type":"email"},
        "item_version": 2, "content_type": "text", "state": "pending", "publishing_action": "published"},
        {"item_id": "456", "headline": "publish via api", "subscriber_id": "#sub_api#",
        "destination": {"format": "ninjs", "delivery_type":"content_api"},
        "item_version": 2, "content_type": "text", "state": "success", "publishing_action": "published"}
      ]}
      """
      Then we assert the content api item "456" is published to subscriber "#sub_api#"
      Then we assert the content api item "456" is not published to subscriber "#sub_direct#"

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
        "content_filter":{"filter_id":"#content_filters._id#", "filter_type": "blocking"}, "product_type": "both"
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
      When we post to "/products" with "direct-product" and success
      """
      {
        "name":"prod-direct","codes":"abc,xyz", "product_type": "direct"
      }
      """
      When we post to "/products" with "api-product" and success
      """
      {
        "name":"prod-api","codes":"abc,xyz", "product_type": "api"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel Direct","media_type":"media", "subscriber_type": "digital",  "email": "test@test.com",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "products": ["#direct-product#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel API","media_type":"media", "subscriber_type": "digital",  "email": "test@test.com",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "api_products": ["#api-product#"]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
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
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
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
      Then we get response code 200

    @auth @notification
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
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
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
      """
        {"publish_schedule": "#DATE+2#"}
      """
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "scheduled", "operation": "publish", "firstpublished": "__future__"}
      """
      And we get expiry for schedule and embargo content 60 minutes after "#archive_publish.publish_schedule#"
      When we get "/published"
      Then we get list with 1 items
      """
      {
        "_items": [
          {
            "_id": "123", "type": "text", "state": "scheduled",
            "_current_version": 2, "operation": "publish", "queue_state": "pending"
          }
        ]
      }
      """
      When we enqueue published
      Then we get notifications
      """
      [{"event": "content:update"}]
      """
      When we get "/publish_queue"
      Then we get list with 0 items
      When we get "/legal_archive/123"
      Then we get error 404
      When the publish schedule lapses
      """
      ["123"]
      """
      When we enqueue published
      And we get "/published"
      Then we get list with 1 items
      """
      {
        "_items": [
          {
            "_id": "123", "type": "text", "state": "published",
            "_current_version": 3, "operation": "publish", "queue_state": "queued"
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
      When we get "/legal_archive/123"
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "published", "type": "text", "task":{"desk": "#desks.name#"}}
      """
      When we expire items
      """
      ["123"]
      """
      And we get "/published"
      Then we get list with 0 items
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 0 items
      When we get "/archived"
      Then we get list with 1 items
      """
      {"_items" : [
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
        "publish_schedule":"2030-02-13T22:46:19.000Z",
        "schedule_settings": {"time_zone": "Australia/Sydney"}
      }
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
      When we get "/archive"
      Then we get list with 1 items
      """
      {
        "_items":
          [
            {"publish_schedule":  "2030-02-13T22:46:19+0000",
             "schedule_settings":  {"utc_publish_schedule": "2030-02-13T11:46:19+0000"}
            }
          ]
      }
      """
      When we patch "/archive/123"
      """
      {"publish_schedule":  "2030-03-13T22:46:19+0000"}
      """
      Then we get response code 200
      When we get "/archive/123"
      Then we get existing resource
      """
      {"publish_schedule":  "2030-03-13T22:46:19+0000",
       "schedule_settings":  {"utc_publish_schedule": "2030-03-13T11:46:19+0000"}
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
      {"publish_schedule":  "2030-03-13T22:46:19+0000",
       "schedule_settings":  {"utc_publish_schedule": "2030-03-13T22:46:19+0000"}
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
        "body_html": "Test Document body",
        "associations": {"editor_0": null}}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
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
      """
        {"publish_schedule": "#DATE+1#"}
      """
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
                  "_id": "123",
                  "firstpublished": null

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
        "slugline": "test", "type": "text",
        "body_html": "<p>Test Document body</p>\n<p>with a \"quote\"</p>"}]
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
        "name":"Channel 3","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}],
        "api_products": ["#products._id#"]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we enqueue published
      Then we assert the content api item "123" is published to subscriber "#subscribers._id#"
      When we get "/items/123"
      Then we get existing resource
      """
      {"uri": "http://localhost:5400/items/123", "pubstatus": "usable"}
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
      {"_current_version": 2, "state": "killed", "operation": "kill", "pubstatus": "canceled", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}, "version_creator": "#CONTEXT_USER_ID#"}
      """
      Then we get OK response
      When we enqueue published
      Then we assert the content api item "123" is published to subscriber "#subscribers._id#"
      When we get "/items/123"
      Then we get existing resource
      """
      {"uri": "http://localhost:5400/items/123", "pubstatus": "canceled"}
      """

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
      When we enqueue published
      When we get "/legal_archive/123"
      Then we get OK response
      When we get "/legal_archive/123?version=all"
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
      {"_current_version": 2, "state": "corrected", "operation": "correct", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"},
       "lock_user": "__none__"
      }
      """
      When we enqueue published
      When we post to "/archive/#archive._id#/unlock"
      """
      {}
      """
      Then we get error 400
      When we get "/legal_archive/123"
      Then we get OK response
      When we get "/legal_archive/123?version=all"
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
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
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
          {"item_version": 2, "publishing_action": "published", "item_id": "123",
           "destination": {"delivery_type": "email"}},
          {"item_version": 3, "publishing_action": "corrected", "item_id": "123",
           "destination": {"delivery_type": "email"}},
          {"item_version": 4, "publishing_action": "killed", "item_id": "123",
           "destination": {"delivery_type": "email"}}
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

    @auth @vocabulary
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
        "anpa_category": [{"qcode": "a"}, {"qcode": "s"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
      """
      When we post to "/filter_conditions" with success
      """
      [{"name": "national", "field": "anpa_category", "operator": "in", "value": "a"}]
      """
      When we post to "/content_filters" with success
      """
      [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "national-only"}]
      """
      When we post to "/products" with "national-product" and success
      """
      {
        "name":"prod-national","codes":"abc,xyz", "product_type": "both",
        "content_filter":{"filter_id":"#content_filters._id#", "filter_type": "permitting"}
      }
      """
      When we post to "/filter_conditions" with success
      """
      [{"name": "sport", "field": "anpa_category", "operator": "in", "value": "s"}]
      """
      When we post to "/content_filters" with success
      """
      [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "sport-only"}]
      """
      When we post to "/products" with "sport-product" and success
      """
      {
        "name":"prod-sport","codes":"abc,xyz", "product_type": "api",
        "content_filter":{"filter_id":"#content_filters._id#", "filter_type": "permitting"}
      }
      """
      And we post to "/subscribers" with "sub1" and success
      """
      {
        "name":"Channel direct","media_type":"media", "subscriber_type": "wire",
        "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#national-product#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we post to "/subscribers" with "sub2" and success
      """
      {
        "name":"Channel api","media_type":"media", "subscriber_type": "wire",
        "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "api_products": ["#sport-product#"]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we enqueue published
      Then we assert the content api item "123" is published to subscriber "#sub2#"
      Then we assert the content api item "123" is not published to subscriber "#sub1#"
      When we patch "/subscribers/#sub2#"
      """
      {
        "api_products": ["#national-product#"]
      }
      """
      Then we get OK response
      When we post to "/archive/#archive._id#/lock"
      """
      {}
      """
      Then we get OK response
      When we publish "#archive._id#" with "correct" type and "corrected" state
      """
      {"headline": "test-1", "anpa_category": [{"qcode": "s"}]}
      """
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "corrected", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we enqueue published
      Then we assert the content api item "123" is published to subscriber "#sub2#"
      Then we assert the content api item "123" is not published to subscriber "#sub1#"
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
      Scenario: Publish a content directly which is marked not-for-publication should fail
      Given "desks"
      """
      [{"name": "Sports"}]
      """
      When we post to "/archive" with success
      """
      [{"guid": "123", "headline": "test",
        "body_html": "body", "state": "fetched",
        "slugline": "test",
        "flags": {"marked_for_not_publication": false},
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      """
      {"flags": {"marked_for_not_publication": true}}
      """
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
        "name":"prod-1","codes":"abc,xyz", "product_type": "direct"
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
      Then we get error 400
      """
      {
        "_issues": {
          "validator exception": "[['DATELINE is a required field']]",
          "fields": {
            "dateline": {
              "located": "required field",
              "date": "required field",
              "source": "required field",
              "text": "required field"
            }
          }
        },
        "_status": "ERR"
      }
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
        "body_html": "Test Document body",
        "dateline": {
          "date": "#DATE#",
          "located" : {
              "country" : "Afghanistan",
              "tz" : "Asia/Kabul",
              "city" : "Mazar-e Sharif",
              "alt_name" : "",
              "country_code" : "AF",
              "city_code" : "Mazar-e Sharif",
              "dateline" : "city",
              "state" : "Balkh",
              "state_code" : "AF.30"
          },
          "text" : "MAZAR-E SHARIF, Dec 30  -",
          "source": "AAP"}
        }]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
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
                      "mandatory_in_list": {"scheme": {"subject": {"required": "true"}, "category": {"required": "true"}}},
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
                    {"name": "arkeologi", "qcode": "01001000", "scheme": "subject", "parent": "01000000"}],
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
                      "mandatory_in_list": {"scheme": {"subject_custom": {"required": "true"}, "category": {"required": "true"}}},
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
                      "mandatory_in_list": {"scheme": {"subject": {"required": "true"}, "category": {"required": "true"}}},
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
        "associations": {
            "featureimage": {
                "_id": "234",
                "guid": "234",
                "alt_text": "alt_text",
                "description_text": "description_text",
                "type": "picture",
                "slugline": "s234",
                "state": "in_progress"}}}]
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
      Then we get error 400
      """
      {"_issues": {"validator exception": "[[\"MEDIA'S HEADLINE is a required field\"]]"}, "_status": "ERR"}
      """

    @auth
    Scenario: Publish fails when embedded item does not exist
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
        "associations": {
            "featureimage": {
                "_id": "234",
                "guid": "234",
                "headline": "Test",
                "alt_text": "alt_text",
                "description_text": "description_text",
                "type": "picture",
                "slugline": "s234",
                "state": "in_progress"}}}]
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
      Then we get error 400
      """
      {"_issues": {"validator exception": "400: Associated item \"featureimage\" does not exist in the system"}, "_status": "ERR"}
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
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
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
      And we get content expiry 60
      When we get "/published/123"
      Then we get OK response
      And we get content expiry 180
      And we get content expiry 180
      When we get "/published/456"
      Then we get OK response
      And we get content expiry 60
      And we get content expiry 60

    @auth
    @vocabulary
    Scenario: Publish with required user defined vocabulary
      Given "desks"
      """
      [{"name": "News", "content_expiry": 180}]
      """
      And "vocabularies"
      """
      [{
          "_id": "vocabulary1",
          "display_name": "Vocabulary 1",
          "schema": {"name" : {}, "qcode": {}, "parent": {}},
          "service": {"all": 1},
          "type": "manageable",
          "items": [{"name": "Option 1", "qcode": "o1", "is_active": true}, {"name": "Option 2", "qcode": "o2", "is_active": true}]
      },{
          "_id": "custom_field_1",
          "display_name": "Custom Field 1",
          "field_type": "text",
          "schema": {"name" : {}, "qcode": {}, "parent": {}},
          "service": {"all": 1},
          "type": "manageable",
          "items": [],
          "field_options": {"single": true}
      }]
      """
      And "content_types"
      """
      [{
          "enabled": true, "priority": 0, "label": "Profile 1",
          "schema": {
              "custom_field_1": {"type": "string", "required": true, "enabled": true},
              "subject": {
                "schema": {
                    "schema": {
                        "qcode": {},
                        "parent": {"nullable" : true},
                        "name": {},
                        "service": {"nullable" : true},
                        "scheme": {
                            "nullable": true,
                            "required": true,
                            "allowed": ["vocabulary1"],
                            "type": "string"
                        }
                    },
                    "type": "dict"
                },
                "mandatory_in_list": {"scheme": {"subject": {"required": "true"}}},
                "default": [],
                "nullable": false,
                "required": true,
                "type": "list",
                "minlength": 1
            }
          }
      }]
      """
      And "archive"
      """
      [{
          "type": "text", "profile": "#content_types._id#", "state": "in_progress",
          "subject": [{"scheme": "subject", "name": "Option 1", "qcode": "o1"}],
          "extra": {"custom_field_1": "some text"}
      }]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
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
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {
        "_current_version": 2,
        "type": "text",
        "state": "published",
        "pubstatus": "usable"
       }
      """

    @auth
    Scenario: Publish associated items and move them to the output stage on main item publish
      Given "vocabularies"
      """
      [
        {"_id": "media", "field_type": "media", "field_options": {"allowed_types": {"picture": true}}},
        {"_id": "related", "field_type": "related_content"}
      ]
      """
      And "content_types"
      """
      [{
          "_id": "profile1", "label": "Profile 1",
          "is_used": true, "enabled": true, "priority": 0, "editor": {},
          "schema": {"media": {"required": true, "type": "media"}}
      }, {
        "_id": "profile2", "schema": {}
      }]
      """
      And "validators"
      """
      [
          {"_id": "publish_picture", "act": "publish", "type": "picture", "schema":{}},
          {"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}
      ]
      """
      And "desks"
      """
      [{"name": "Sports"}]
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
      And we post to "archive" with success
      """
      [
        {
          "_id": "text", "guid": "text", "type": "text", "headline": "text", "state": "in_progress", "profile": "profile2"
        },
        {
               "guid": "234", "type": "picture", "slugline": "234", "headline": "234", "state": "in_progress",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
            "renditions": {}
        },
          {
              "guid": "123", "type": "text", "headline": "test", "state": "in_progress", "profile": "profile1",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
            "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body",
            "associations": {
                "media--1": {
                    "_id": "234",
                    "guid": "234",
                    "type": "picture",
                    "slugline": "234",
                    "headline": "234",
                    "alt_text": "alt_text",
                    "description_text": "description_text",
                    "state": "in_progress",
                    "renditions": {},
                    "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}
                },
                "related--1": {
                  "_id": "text",
                  "type": "text",
                  "order": "1"
                }
            }
          }
      ]
      """
      And we publish "123" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {
        "_current_version": 2,
        "type": "text",
        "state": "published",
        "associations": {
            "media--1": {
              "state": "published",
              "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}
            }
        },
        "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}
      }
      """
      When we get "/archive/234"
      Then we get existing resource
      """
      {
          "guid": "234",
          "state": "published",
          "task":{"desk": "#desks._id#"}
      }
      """
      When we get "/published"
      Then we get list with 3 items
      """
      {"_items": [{
        "guid": "123",
        "associations": {
          "media--1": {
            "_id": "234",
            "type": "picture",
            "state": "published",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}
          },
          "related--1": {
            "_id": "text",
            "type": "text",
            "state": "__no_value__"
          }
        }
      }]}
      """
      When we get "/archive/123"
      Then we get existing resource
      """
      {
        "associations": {
          "media--1": {
            "_id": "234",
            "type": "picture",
            "state": "published"
          },
          "related--1": {
            "_id": "text",
            "type": "text",
            "state": "__no_value__"
          }
        }
      }
      """

    @auth
    Scenario: Correct associated items updates the fields
      Given "vocabularies"
      """
      [{
          "_id": "media1", "field_type": "media",
          "display_name": "Media 1", "type": "manageable",
          "service": {"all": 1}, "items": [],
          "field_options": {"allowed_types": {"picture": true}},
          "schema": {"parent": {}, "name": {}, "qcode": {}}
      }, {
      	"_id": "crop_sizes",
      	"unique_field": "name",
      	"items": [
      		{"is_active": true, "name": "original", "width": 800, "height": 600}
      	]
      }
      ]
      """
      And "content_types"
      """
      [{
          "_id": "profile1", "label": "Profile 1",
          "is_used": true, "enabled": true, "priority": 0, "editor": {},
          "schema": {"media1": {"required": true, "nullable": false, "enabled": true, "type": "media"}}
      }]
      """
      And "validators"
      """
      [
          {"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
          {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
          {
            "_id": "publish_picture",
            "act": "publish",
            "type": "picture",
            "schema": {
                "renditions": {
                    "type": "dict",
                    "required": true,
                    "schema": {"original": {"type": "dict", "required": true}}
                }
            }
        },
        {
            "_id": "correct_picture",
            "act": "correct",
            "type": "picture",
            "schema": {
                "renditions": {
                    "type": "dict",
                    "required": false,
                    "schema": {"original": {"type": "dict", "required": true}}
                }
            }
        }
      ]
      """
      And "desks"
      """
      [{"name": "Sports"}]
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
      And we post to "archive" with success
      """
      [
          {
               "guid": "234", "type": "picture", "slugline": "234", "headline": "234", "state": "in_progress",
               "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
               "renditions": {
                  "original": {"CropLeft": 0, "CropRight": 800, "CropTop": 0, "CropBottom": 600}
               }
          },
          {
              "guid": "123", "type": "text", "headline": "test", "state": "in_progress",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
            "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body",
            "associations": {
                "featuremedia": {
                    "_id": "234",
                    "guid": "234",
                    "type": "picture",
                    "slugline": "234",
                    "headline": "234",
                    "byline": "xyz",
                    "alt_text": "alt_text",
                    "description_text": "description_text",
                    "state": "in_progress",
                    "renditions": {
                        "original": {"CropLeft": 0, "CropRight": 800, "CropTop": 0, "CropBottom": 600}
                     },
                    "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}
                }
            }
           }
      ]
      """
      And we publish "123" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {
        "_current_version": 2,
        "type": "text",
        "state": "published",
        "associations": {
            "featuremedia": {"state": "published"}
        },
        "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}
      }
      """
      When we publish "123" with "correct" type and "corrected" state
      """
      {
        "associations": {
            "featuremedia": {
                "byline": "foo",
                "alt_text": "alt_text",
                "description_text": "description_text",
                "headline": "234",
                "renditions": {
                      "original": {"CropLeft": 0, "CropRight": 800, "CropTop": 0, "CropBottom": 600}
                   }
                }
            }
      }
      """
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "corrected", "associations": {"featuremedia": {"byline": "foo"}}}
      """

    @auth
    Scenario: Publish with success when associated item contains _type field
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
      [{"_id": "234", "guid": "234", "type": "picture", "slugline": "s234", "state": "in_progress",
        "headline": "some headline", "_current_version": 1},
       {"guid": "123", "type": "text", "headline": "test", "_current_version": 1, "state": "in_progress",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body",
        "associations": {"editor_0": {
            "_id": "234",
            "guid": "234",
            "type": "picture",
            "slugline": "s234",
            "state": "in_progress",
            "headline": "some headline",
            "alt_text": "alt_text",
            "description_text": "description_text",
            "_type": "archive",
            "_current_version": 1
        }}}]
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
      {
        "guid": "123",
        "state": "published",
        "associations": {
            "editor_0": {"state": "published"}
        }
      }
      """

    @auth
    @vocabulary
    Scenario: Compare embedded items for content API and HTTP push destinations
      Given empty "filter_conditions"
      Given empty "content_filters"
      Given empty "products"
      Given empty "subscribers"
      Given "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"_id": "234", "guid": "234", "type": "picture", "slugline": "s234", "state": "in_progress",
        "headline": "some headline", "_current_version": 1,
        "renditions": {"original": {"mimetype": "audio/mp3", "media": "5ae35d0095cc644f859a94c2",
            "href": "http://localhost:5000/api/upload-raw/5ae35d0095cc644f859a94c2"
        }}},
       {"guid": "123", "type": "text", "headline": "fc_api", "_current_version": 1, "state": "in_progress",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body",
        "associations": {"media--1": {
            "_id": "234", "guid": "234", "type": "picture", "slugline": "s234", "state": "in_progress",
            "headline": "some headline", "_type": "archive", "_current_version": 1,
            "renditions": {"original": {"mimetype": "audio/mp3", "media": "5ae35d0095cc644f859a94c2",
                "href": "http://localhost:5000/api/upload-raw/5ae35d0095cc644f859a94c2"
        }}}}}]
      """
      When we post to "/filter_conditions" with "fc_api" and success
      """
      [{"name": "fc_api", "field": "headline", "operator": "like", "value": "api"}]
      """
      When we post to "/content_filters" with "cf_api" and success
      """
      [{"content_filter": [{"expression": {"fc": ["#fc_api#"]}}], "name": "cf_api"}]
      """
      And we post to "/products" with "p_api" and success
      """
      [{
        "name":"prod-2","codes":"api",
        "content_filter":{"filter_id":"#cf_api#", "filter_type": "permitting"},
        "product_type": "api"
      }]
      """
      And we post to "/subscribers" with "sub_api" and success
      """
      {
        "name":"Channel API","media_type":"media", "subscriber_type": "wire",  "email": "test@test.com",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "api_products": ["#p_api#"]
      }
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
      And we post to "/subscribers" with "sub_reg" and success
      """
      {
        "name":"Subscriber 1","media_type":"media", "subscriber_type": "digital",
        "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "ninjs", "delivery_type":"http_push","config":{}}]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {
        "guid": "123", "state": "published",
        "associations": {"media--1": {"state": "published"}}
      }
      """
      When we enqueue published
      When we get "/publish_queue"
      Then we get 3 queued items
      """
      {
        "_items": [
            {
                "item_id": "123", "state": "success", "content_type": "text",
                "subscriber_id": "#sub_api#", "item_version": 2, "ingest_provider": "__none__",
                "destination": {
                    "delivery_type": "content_api", "format": "ninjs", "name": "content api"
                },
                "formatted_item": {
                    "guid": "123", "version": "2", "headline": "fc_api", "body_html": "Test Document body",
                    "language": "en", "pubstatus": "usable", "type": "text",
                    "associations": {
                        "media--1": {
                            "guid": "234", "headline": "some headline", "language": "en",
                            "slugline": "s234", "pubstatus": "usable", "type": "picture",
                            "renditions": {
                                "original": {
                                    "mimetype": "audio/mp3", "media": "5ae35d0095cc644f859a94c2",
                                    "href": "http://localhost:5000/api/upload-raw/5ae35d0095cc644f859a94c2",
                                    "media": "5ae35d0095cc644f859a94c2"
                                }
                            }
                        }
                    }
                }
            },
            {
                "item_id": "123", "state": "pending", "content_type": "text",
                "subscriber_id": "#sub_reg#", "item_version": 2, "ingest_provider": "__none__",
                "destination": {
                    "delivery_type": "http_push", "format": "ninjs", "name": "Test"
                },
                "formatted_item": {
                    "guid": "123", "version": "2", "headline": "fc_api", "body_html": "Test Document body",
                    "language": "en", "pubstatus": "usable", "type": "text",
                    "associations": {
                        "media--1": {
                            "guid": "234", "headline": "some headline", "language": "en",
                            "slugline": "s234", "pubstatus": "usable", "type": "picture",
                            "renditions": {
                                "original": {
                                    "mimetype": "audio/mp3", "media": "5ae35d0095cc644f859a94c2",
                                    "href": "http://localhost:5000/api/upload-raw/5ae35d0095cc644f859a94c2",
                                    "media": "5ae35d0095cc644f859a94c2"
                                }
                            }
                        }
                    }
                }
            }
          ]
      }
      """

    @auth
    Scenario: We can lock a published content and then correct it and then takedown the article
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
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
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
      When we publish "#archive._id#" with "takedown" type and "recalled" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 4, "state": "recalled", "operation": "takedown", "pubstatus": "canceled", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      And we get updated timestamp "versioncreated"
      When we enqueue published
      When we get "/legal_archive/123"
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 4, "state": "recalled"}
      """
      When we get "/legal_archive/123?version=all"
      Then we get list with 4 items
      """
      {
        "_items":[
          {"_current_version": 1, "state": "fetched"},
          {"_current_version": 2, "state": "published"},
          {"_current_version": 3, "state": "corrected"},
          {"_current_version": 4, "state": "recalled"}
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
          {"item_version": 2, "publishing_action": "published", "item_id": "123",
           "destination": {"delivery_type": "email"}},
          {"item_version": 3, "publishing_action": "corrected", "item_id": "123",
           "destination": {"delivery_type": "email"}},
          {"item_version": 4, "publishing_action": "recalled", "item_id": "123",
           "destination": {"delivery_type": "email"}}
        ]
      }
      """

    @auth
    Scenario: Send correction with new featuremedia which does not fill all renditions
      Given the "validators"
        """
        [
            {"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
            {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
            {"_id": "publish_picture", "act": "publish", "type": "picture", "schema":{}},
            {"_id": "correct_picture", "act": "correct", "type": "picture", "schema":{}}
        ]
        """
      And "desks"
        """
        [{"name": "Sports", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
        """
      And "vocabularies"
      """
      [{
        "_id": "crop_sizes",
        "unique_field": "name",
        "items": [
          {"is_active": true, "name": "600x800", "width": 800, "height": 600},
          {"is_active": true, "name": "1200x720", "width": 1280, "height": 720}
        ]
      }]
      """
      And "archive"
        """
        [
            {
              "_id": "feature_media_id",
              "guid": "feature_media_guid",
              "type": "picture",
              "headline": "Image",
              "pubstatus": "usable",
              "_current_version" : 1,
              "flags": {
                "marked_for_not_publication": false,
                "marked_for_legal": false,
                "marked_archived_only": false,
                "marked_for_sms": false
              },
              "format": "HTML",
              "original_creator": "5cda8c5cfe985e059b638ee8",
              "unique_id": 65,
              "unique_name": "#65",
              "state": "in_progress",
              "source": "Superdesk",
              "renditions": {
                "original": {
                  "href": "http://localhost:5000/api/upload-raw/orig.jpg",
                  "media": "orig",
                  "mimetype": "image/jpeg",
                  "width": 4032,
                  "height": 3024,
                  "poi": {
                    "x": 3024,
                    "y": 756
                  }
                },
                "baseImage": {
                  "href": "http://localhost:5000/api/upload-raw/baseImage.jpg",
                  "media": "baseImage",
                  "mimetype": "image/jpeg",
                  "width": 1400,
                  "height": 1050,
                  "poi": {
                    "x": 1050,
                    "y": 262
                  }
                },
                "thumbnail": {
                  "href": "http://localhost:5000/api/upload-raw/thumbnail.jpg",
                  "media": "thumbnail",
                  "mimetype": "image/jpeg",
                  "width": 160,
                  "height": 120,
                  "poi": {
                    "x": 120,
                    "y": 30
                  }
                },
                "viewImage": {
                  "href": "http://localhost:5000/api/upload-raw/viewImage.jpg",
                  "media": "viewImage",
                  "mimetype": "image/jpeg",
                  "width": 640,
                  "height": 480,
                  "poi": {
                    "x": 480,
                    "y": 120
                  }
                },
                "600x800": {
                  "poi": {
                    "x": 3012,
                    "y": 759
                  },
                  "CropLeft": 12,
                  "CropRight": 4032,
                  "CropTop": -3,
                  "CropBottom": 3024,
                  "width": 800,
                  "height": 600,
                  "href": "http://localhost:5000/api/upload-raw/600x800.jpg",
                  "media": "600x800",
                  "mimetype": "image/jpeg"
                },
                "1280x720": {
                  "poi": {
                    "x": 3024,
                    "y": 756
                  },
                  "CropLeft": 0,
                  "CropRight": 4032,
                  "CropTop": 0,
                  "CropBottom": 2277,
                  "width": 1280,
                  "height": 720,
                  "href": "http://localhost:5000/api/upload-raw/1280x720.jpg",
                  "media": "1280x720",
                  "mimetype": "image/jpeg"
                }
              },
              "mimetype": "image/jpeg"
            },
            {
                "_id": "item_id",
                "guid": "item_guid",
                "headline": "original item",
                "state": "in_progress",
                "associations": {
                    "featuremedia": {
                        "_id": "feature_media_id",
                        "media": "5c13867efe985edfc9223480",
                        "type": "picture",
                        "headline": "picture headline",
                        "alt_text": "alt_text",
                        "description_text": "description_text",
                        "format": "HTML",
                        "renditions": {
                            "original": {
                                "href": "http://localhost:5000/api/upload-raw/orig.jpg",
                                "media": "orig",
                                "mimetype": "image/jpeg",
                                "width": 4032,
                                "height": 3024,
                                "poi": {
                                    "x": 3024,
                                    "y": 756
                                }
                            },
                            "baseImage": {
                                "href": "http://localhost:5000/api/upload-raw/baseImage.jpg",
                                "media": "baseImage",
                                "mimetype": "image/jpeg",
                                "width": 1400,
                                "height": 1050,
                                "poi": {
                                    "x": 1050,
                                    "y": 262
                                }
                            },
                            "thumbnail": {
                                "href": "http://localhost:5000/api/upload-raw/thumbnail.jpg",
                                "media": "thumbnail",
                                "mimetype": "image/jpeg",
                                "width": 160,
                                "height": 120,
                                "poi": {
                                    "x": 120,
                                    "y": 30
                                }
                            },
                            "viewImage": {
                                "href": "http://localhost:5000/api/upload-raw/viewImage.jpg",
                                "media": "viewImage",
                                "mimetype": "image/jpeg",
                                "width": 640,
                                "height": 480,
                                "poi": {
                                    "x": 480,
                                    "y": 120
                                }
                            },
                            "600x800": {
                                "poi": {
                                    "x": 3012,
                                    "y": 759
                                },
                                "CropLeft": 12,
                                "CropRight": 4032,
                                "CropTop": -3,
                                "CropBottom": 3024,
                                "width": 800,
                                "height": 600,
                                "href": "http://localhost:5000/api/upload-raw/600x800.jpg",
                                "media": "600x800",
                                "mimetype": "image/jpeg"
                            },
                            "1280x720": {
                                "poi": {
                                    "x": 3024,
                                    "y": 756
                                },
                                "CropLeft": 0,
                                "CropRight": 4032,
                                "CropTop": 0,
                                "CropBottom": 2277,
                                "width": 1280,
                                "height": 720,
                                "href": "http://localhost:5000/api/upload-raw/1280x720.jpg",
                                "media": "1280x720",
                                "mimetype": "image/jpeg"
                            }
                        }
                    }
                }
            }
        ]
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
      When we publish "#archive._id#" with "correct" type and "corrected" state
        """
        {
            "headline": "corrected item",
            "associations": {
                "featuremedia": {
                    "_id": "feature_media_id",
                    "media": "5c13867efe985edfc9223480",
                    "type": "picture",
                    "headline": "picture headline",
                    "alt_text": "alt_text",
                    "description_text": "description_text",
                    "format": "HTML",
                    "renditions": {
                         "original": {
                            "href": "http://localhost:5000/api/upload-raw/orig_new.jpg",
                            "media": "orig_new",
                            "mimetype": "image/jpeg",
                            "width": 4032,
                            "height": 3024,
                            "poi": {
                                "x": 3024,
                                "y": 756
                            }
                        },
                        "baseImage": {
                            "href": "http://localhost:5000/api/upload-raw/baseImage_new.jpg",
                            "media": "baseImage_new",
                            "mimetype": "image/jpeg",
                            "width": 1400,
                            "height": 1050,
                            "poi": {
                                "x": 1050,
                                "y": 262
                            }
                        },
                        "thumbnail": {
                            "href": "http://localhost:5000/api/upload-raw/thumbnail_new.jpg",
                            "media": "thumbnail_new",
                            "mimetype": "image/jpeg",
                            "width": 160,
                            "height": 120,
                            "poi": {
                                "x": 120,
                                "y": 30
                            }
                        },
                        "viewImage": {
                            "href": "http://localhost:5000/api/upload-raw/viewImage_new.jpg",
                            "media": "viewImage_new",
                            "mimetype": "image/jpeg",
                            "width": 640,
                            "height": 480,
                            "poi": {
                                "x": 480,
                                "y": 120
                            }
                        },
                        "600x800": {
                            "poi": {
                                "x": 3012,
                                "y": 759
                            },
                            "CropLeft": 12,
                            "CropRight": 4032,
                            "CropTop": -3,
                            "CropBottom": 3024,
                            "width": 800,
                            "height": 600,
                            "href": "http://localhost:5000/api/upload-raw/600x800_new.jpg",
                            "media": "600x800_new",
                            "mimetype": "image/jpeg"
                        }
                    }
                }
            }
        }
        """
      Then we get OK response
      And we get existing resource
        """
        {
            "headline": "corrected item",
            "state": "corrected",
            "associations": {
                "featuremedia": {
                    "_id": "feature_media_id",
                    "media": "5c13867efe985edfc9223480",
                    "type": "picture",
                    "headline": "picture headline",
                    "alt_text": "alt_text",
                    "description_text": "description_text",
                    "format": "HTML",
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/orig_new.jpg",
                            "media": "orig_new",
                            "mimetype": "image/jpeg",
                            "width": 4032,
                            "height": 3024,
                            "poi": {
                                "x": 3024,
                                "y": 756
                            }
                        },
                        "baseImage": {
                            "href": "http://localhost:5000/api/upload-raw/baseImage_new.jpg",
                            "media": "baseImage_new",
                            "mimetype": "image/jpeg",
                            "width": 1400,
                            "height": 1050,
                            "poi": {
                                "x": 1050,
                                "y": 262
                            }
                        },
                        "thumbnail": {
                            "href": "http://localhost:5000/api/upload-raw/thumbnail_new.jpg",
                            "media": "thumbnail_new",
                            "mimetype": "image/jpeg",
                            "width": 160,
                            "height": 120,
                            "poi": {
                                "x": 120,
                                "y": 30
                            }
                        },
                        "viewImage": {
                            "href": "http://localhost:5000/api/upload-raw/viewImage_new.jpg",
                            "media": "viewImage_new",
                            "mimetype": "image/jpeg",
                            "width": 640,
                            "height": 480,
                            "poi": {
                                "x": 480,
                                "y": 120
                            }
                        },
                        "600x800": {
                            "poi": {
                                "x": 3012,
                                "y": 759
                            },
                            "CropLeft": 12,
                            "CropRight": 4032,
                            "CropTop": -3,
                            "CropBottom": 3024,
                            "width": 800,
                            "height": 600,
                            "href": "http://localhost:5000/api/upload-raw/600x800_new.jpg",
                            "media": "600x800_new",
                            "mimetype": "image/jpeg"
                        },
                        "1280x720": "__none__"
                    }
                }
            }
        }
        """

    @auth
    Scenario: Removed association items should not get published on correction
      Given config update
      """
      { "PUBLISH_ASSOCIATED_ITEMS": true}
      """
      And "validators"
        """
        [
            {"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
            {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
            {"_id": "publish_picture", "act": "publish", "type": "picture", "schema":{}},
            {"_id": "correct_picture", "act": "correct", "type": "picture", "schema":{}}
        ]
        """
      And "desks"
        """
        [{"name": "Sports", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
        """
      And "vocabularies"
      """
      [{
        "_id": "crop_sizes",
        "unique_field": "name",
        "items": [
          {"is_active": true, "name": "600x800", "width": 800, "height": 600},
          {"is_active": true, "name": "1200x720", "width": 1280, "height": 720}
        ]
      }]
      """
      And "archive"
        """
        [
            {
              "_id": "feature_media_id",
              "guid": "feature_media_guid",
              "type": "picture",
              "headline": "Image",
              "pubstatus": "usable",
              "_current_version" : 1,
              "flags": {
                "marked_for_not_publication": false,
                "marked_for_legal": false,
                "marked_archived_only": false,
                "marked_for_sms": false
              },
              "format": "HTML",
              "original_creator": "5cda8c5cfe985e059b638ee8",
              "unique_id": 65,
              "unique_name": "#65",
              "state": "in_progress",
              "source": "Superdesk",
              "renditions": {
                "original": {
                  "href": "http://localhost:5000/api/upload-raw/orig.jpg",
                  "media": "orig",
                  "mimetype": "image/jpeg",
                  "width": 4032,
                  "height": 3024,
                  "poi": {
                    "x": 3024,
                    "y": 756
                  }
                },
                "baseImage": {
                  "href": "http://localhost:5000/api/upload-raw/baseImage.jpg",
                  "media": "baseImage",
                  "mimetype": "image/jpeg",
                  "width": 1400,
                  "height": 1050,
                  "poi": {
                    "x": 1050,
                    "y": 262
                  }
                },
                "thumbnail": {
                  "href": "http://localhost:5000/api/upload-raw/thumbnail.jpg",
                  "media": "thumbnail",
                  "mimetype": "image/jpeg",
                  "width": 160,
                  "height": 120,
                  "poi": {
                    "x": 120,
                    "y": 30
                  }
                },
                "viewImage": {
                  "href": "http://localhost:5000/api/upload-raw/viewImage.jpg",
                  "media": "viewImage",
                  "mimetype": "image/jpeg",
                  "width": 640,
                  "height": 480,
                  "poi": {
                    "x": 480,
                    "y": 120
                  }
                },
                "600x800": {
                  "poi": {
                    "x": 3012,
                    "y": 759
                  },
                  "CropLeft": 12,
                  "CropRight": 4032,
                  "CropTop": -3,
                  "CropBottom": 3024,
                  "width": 800,
                  "height": 600,
                  "href": "http://localhost:5000/api/upload-raw/600x800.jpg",
                  "media": "600x800",
                  "mimetype": "image/jpeg"
                },
                "1280x720": {
                  "poi": {
                    "x": 3024,
                    "y": 756
                  },
                  "CropLeft": 0,
                  "CropRight": 4032,
                  "CropTop": 0,
                  "CropBottom": 2277,
                  "width": 1280,
                  "height": 720,
                  "href": "http://localhost:5000/api/upload-raw/1280x720.jpg",
                  "media": "1280x720",
                  "mimetype": "image/jpeg"
                }
              },
              "mimetype": "image/jpeg"
            },
            {
                "_id": "item_id",
                "guid": "item_guid",
                "headline": "original item",
                "state": "in_progress",
                "associations": {
                    "featuremedia": {
                        "_id": "feature_media_id",
                        "media": "5c13867efe985edfc9223480",
                        "type": "picture",
                        "headline": "picture headline",
                        "alt_text": "alt_text",
                        "description_text": "description_text",
                        "format": "HTML",
                        "renditions": {
                            "original": {
                                "href": "http://localhost:5000/api/upload-raw/orig.jpg",
                                "media": "orig",
                                "mimetype": "image/jpeg",
                                "width": 4032,
                                "height": 3024,
                                "poi": {
                                    "x": 3024,
                                    "y": 756
                                }
                            },
                            "baseImage": {
                                "href": "http://localhost:5000/api/upload-raw/baseImage.jpg",
                                "media": "baseImage",
                                "mimetype": "image/jpeg",
                                "width": 1400,
                                "height": 1050,
                                "poi": {
                                    "x": 1050,
                                    "y": 262
                                }
                            },
                            "thumbnail": {
                                "href": "http://localhost:5000/api/upload-raw/thumbnail.jpg",
                                "media": "thumbnail",
                                "mimetype": "image/jpeg",
                                "width": 160,
                                "height": 120,
                                "poi": {
                                    "x": 120,
                                    "y": 30
                                }
                            },
                            "viewImage": {
                                "href": "http://localhost:5000/api/upload-raw/viewImage.jpg",
                                "media": "viewImage",
                                "mimetype": "image/jpeg",
                                "width": 640,
                                "height": 480,
                                "poi": {
                                    "x": 480,
                                    "y": 120
                                }
                            },
                            "600x800": {
                                "poi": {
                                    "x": 3012,
                                    "y": 759
                                },
                                "CropLeft": 12,
                                "CropRight": 4032,
                                "CropTop": -3,
                                "CropBottom": 3024,
                                "width": 800,
                                "height": 600,
                                "href": "http://localhost:5000/api/upload-raw/600x800.jpg",
                                "media": "600x800",
                                "mimetype": "image/jpeg"
                            },
                            "1280x720": {
                                "poi": {
                                    "x": 3024,
                                    "y": 756
                                },
                                "CropLeft": 0,
                                "CropRight": 4032,
                                "CropTop": 0,
                                "CropBottom": 2277,
                                "width": 1280,
                                "height": 720,
                                "href": "http://localhost:5000/api/upload-raw/1280x720.jpg",
                                "media": "1280x720",
                                "mimetype": "image/jpeg"
                            }
                        }
                    }
                }
            }
        ]
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
      When we get "/published"
      Then we get list with 2 items
      When we publish "#archive._id#" with "correct" type and "corrected" state
        """
        {
            "headline": "corrected item",
            "associations": {
                "featuremedia": null
            }
        }
        """
      Then we get OK response
      And we get existing resource
        """
        {
            "headline": "corrected item",
            "state": "corrected",
            "associations": {
                "featuremedia": "__none__"
            }
        }
        """
      When we get "/published"
      Then we get list with 3 items

    @auth
    Scenario: Do not fix-related-references for not _fetchable associations
      Given "vocabularies"
      """
      [
        {"_id": "media", "field_type": "media", "field_options": {"allowed_types": {"picture": true}}},
        {"_id": "belga_related_articles", "field_type": "related_content"}
      ]
      """
      And "content_types"
      """
      [{
          "_id": "profile1", "label": "Profile 1",
          "is_used": true, "enabled": true, "priority": 0, "editor": {},
          "schema": {}
      }]
      """
      And "validators"
      """
      [
          {"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}
      ]
      """
      And "desks"
      """
      [{"name": "Sports"}]
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
      And we post to "archive" with success
      """
      [
          {
            "guid": "123",
            "type": "text",
            "headline": "test",
            "state": "in_progress",
            "profile": "profile1",
            "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body",
            "associations": {
              "belga_related_articles--1" : {
                  "_id" : "urn:belga.be:360archive:FAKEID",
                  "guid" : "urn:belga.be:360archive:FAKEID",
                  "_fetchable" : false,
                  "extra" : {
                      "bcoverage" : "urn:belga.be:360archive:FAKEID"
                  },
                  "type" : "text",
                  "mimetype" : "application/vnd.belga.360archive",
                  "pubstatus" : "usable",
                  "headline" : "Postkantoren blijven vrijdag gesloten",
                  "versioncreated" : "2020-02-26T15:42:05+0000",
                  "firstcreated" : "2020-02-26T15:42:05+0000",
                  "creditline" : "BELGA",
                  "source" : "BELGA",
                  "language" : "nl",
                  "abstract" : "Bpost hanteert nu vrijdag 28 februari een aangepaste dienstregeling",
                  "body_html" : "Bpost hanteert dit jaar vijf dagen met een aangepaste dienstverlening.",
                  "_type" : "externalsource",
                  "fetch_endpoint" : "search_providers_proxy",
                  "ingest_provider" : "5da8572a9e7cb98d13ce1d7b",
                  "selected" : false,
                  "state" : "published",
                  "operation" : "publish"
              }
            }
          }
      ]
      """
      And we publish "123" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {
          "profile": "profile1",
          "type": "text",
          "operation": "publish",
          "state": "published",
          "urgency": 3,
          "language": "en",
          "guid": "123",
          "_id": "123",
          "source": "AAP",
          "headline": "test",
          "associations": {
              "belga_related_articles--1": {
                  "versioncreated": "2020-02-26T15:42:05+0000",
                  "body_html": "Bpost hanteert dit jaar vijf dagen met een aangepaste dienstverlening.",
                  "abstract": "Bpost hanteert nu vrijdag 28 februari een aangepaste dienstregeling",
                  "ingest_provider": "5da8572a9e7cb98d13ce1d7b",
                  "operation": "publish",
                  "state": "published",
                  "_fetchable": false,
                  "extra": {
                      "bcoverage": "urn:belga.be:360archive:FAKEID"
                  },
                  "selected": false,
                  "language": "nl",
                  "guid": "urn:belga.be:360archive:FAKEID",
                  "_id": "urn:belga.be:360archive:FAKEID",
                  "source": "BELGA",
                  "headline": "Postkantoren blijven vrijdag gesloten",
                  "creditline": "BELGA",
                  "firstcreated": "2020-02-26T15:42:05+0000",
                  "mimetype": "application/vnd.belga.360archive",
                  "pubstatus": "usable",
                  "fetch_endpoint": "search_providers_proxy",
                  "type": "text"
              }
          }
      }
      """
      When we get "/archive/123"
      Then we get existing resource
      """
        {
            "associations": {
                "belga_related_articles--1": {
                    "versioncreated": "2020-02-26T15:42:05+0000",
                    "body_html": "Bpost hanteert dit jaar vijf dagen met een aangepaste dienstverlening.",
                    "abstract": "Bpost hanteert nu vrijdag 28 februari een aangepaste dienstregeling",
                    "ingest_provider": "5da8572a9e7cb98d13ce1d7b",
                    "operation": "publish",
                    "state": "published",
                    "_fetchable": false,
                    "extra": {
                        "bcoverage": "urn:belga.be:360archive:FAKEID"
                    },
                    "selected": false,
                    "language": "nl",
                    "guid": "urn:belga.be:360archive:FAKEID",
                    "_id": "urn:belga.be:360archive:FAKEID",
                    "source": "BELGA",
                    "headline": "Postkantoren blijven vrijdag gesloten",
                    "creditline": "BELGA",
                    "firstcreated": "2020-02-26T15:42:05+0000",
                    "mimetype": "application/vnd.belga.360archive",
                    "pubstatus": "usable",
                    "fetch_endpoint": "search_providers_proxy",
                    "type": "text"
                }
            }
        }
        """

    @auth
    Scenario: body_html is generated from draftJS state on correction
        Given "archive"
        """
        [{"_id": "test_editor_gen_1", "guid": "test_editor_gen_1", "headline": "test", "state": "fetched"}]
        """
        When we publish "#archive._id#" with "publish" type and "published" state
        Then we get OK response

        When we publish "#archive._id#" with "correct" type and "corrected" state
        """
        {
            "fields_meta": {
                "body_html": {
                    "draftjsState": [{
                        "blocks": [
                            {
                                "key": "fcbn3",
                                "text": "The name of Highlaws comes from the Old English hēah-hlāw, meaning \"high mounds\".",
                                "type": "unstyled",
                                "depth": 0,
                                "inlineStyleRanges": [],
                                "entityRanges": [],
                                "data": {"MULTIPLE_HIGHLIGHTS": {}}
                            }
                        ],
                        "entityMap": {}
                    }]
                }
            }
        }
        """
        Then we get OK response
        And we get existing resource
        """
        {
            "_id": "test_editor_gen_1",
            "guid": "test_editor_gen_1",
            "headline": "test",
            "state": "corrected",
            "body_html": "<p>The name of Highlaws comes from the Old English hēah-hlāw, meaning \"high mounds\".</p>",
            "fields_meta": {
                "body_html": {
                    "draftjsState": [{
                        "blocks": [
                            {
                                "key": "fcbn3",
                                "text": "The name of Highlaws comes from the Old English hēah-hlāw, meaning \"high mounds\".",
                                "type": "unstyled",
                                "depth": 0,
                                "inlineStyleRanges": [],
                                "entityRanges": [],
                                "data": {"MULTIPLE_HIGHLIGHTS": {}}
                            }
                        ],
                        "entityMap": {}
                    }]
                }
            }
        }
        """

    @auth
    Scenario: Schedule publishing when PUBLISH_ASSOCIATED_ITEMS is on
      Given empty "subscribers"
      Given config update
      """
      { "PUBLISH_ASSOCIATED_ITEMS": true}
      """
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
      [
          {
              "_id": "234",
              "guid": "234",
              "_current_version": 1,
              "type": "picture",
              "slugline": "234",
              "headline": "234",
              "state": "in_progress",
              "task": {
                  "desk": "#desks._id#",
                  "stage": "#desks.incoming_stage#",
                  "user": "#CONTEXT_USER_ID#"
              },
              "renditions": {}
          },
          {
              "_id": "123",
              "guid": "123",
              "_current_version": 1,
              "headline": "main item",
              "slugline": "main item",
              "body_html": "Test Document body",
              "state": "in_progress",
              "task": {
                  "desk": "#desks._id#",
                  "stage": "#desks.incoming_stage#",
                  "user": "#CONTEXT_USER_ID#"
              },
              "associations": {
                  "media--1": {
                      "_id": "234",
                      "_current_version": 1,
                      "guid": "234",
                      "type": "picture",
                      "slugline": "234",
                      "headline": "234",
                      "alt_text": "alt_text",
                      "description_text": "description_text",
                      "state": "in_progress",
                      "renditions": {},
                      "task": {
                          "desk": "#desks._id#",
                          "stage": "#desks.incoming_stage#",
                          "user": "#CONTEXT_USER_ID#"
                      }
                  }
              }
          }
      ]
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
      And we publish "123" with "publish" type and "published" state
      """
      {"publish_schedule": "#DATE+1#", "schedule_settings": {"time_zone": "Europe/Prague"}}
      """
      Then we get OK response
      And we get existing resource
      """
      {
          "_id": "123",
          "guid": "123",
          "_current_version": 2,
          "state": "scheduled",
          "operation": "publish",
          "associations": {
              "media--1": {
                  "_id": "234",
                  "_current_version": 2,
                  "guid": "234",
                  "type": "picture",
                  "slugline": "234",
                  "headline": "234",
                  "alt_text": "alt_text",
                  "description_text": "description_text",
                  "state": "scheduled",
                  "operation": "publish",
                  "schedule_settings": {"time_zone": "Europe/Prague"},
                  "renditions": {}
              }
          }
      }
      """
      When we get "/archive/123"
      Then we get existing resource
      """
      {
          "_id": "123",
          "guid": "123",
          "_current_version": 2,
          "state": "scheduled",
          "operation": "publish",
          "associations": {
              "media--1": {
                  "_id": "234",
                  "_current_version": 2,
                  "guid": "234",
                  "type": "picture",
                  "slugline": "234",
                  "headline": "234",
                  "alt_text": "alt_text",
                  "description_text": "description_text",
                  "state": "scheduled",
                  "operation": "publish",
                  "renditions": {}
              }
          }
      }
      """
      When we get "/archive/234"
      Then we get existing resource
      """
      {
          "_id": "234",
          "_current_version": 2,
          "guid": "234",
          "type": "picture",
          "slugline": "234",
          "headline": "234",
          "alt_text": "alt_text",
          "description_text": "description_text",
          "state": "scheduled",
          "operation": "publish",
          "renditions": {}
      }
      """
      When we patch "/archive/123"
      """
      {"publish_schedule": null}
      """
      Then we get OK response
      And we get existing resource
      """
      {
          "_id": "123",
          "guid": "123",
          "state": "in_progress",
          "operation": "deschedule",
          "associations": {
              "media--1": {
                  "_id": "234",
                  "guid": "234",
                  "type": "picture",
                  "slugline": "234",
                  "headline": "234",
                  "alt_text": "alt_text",
                  "description_text": "description_text",
                  "state": "in_progress",
                  "operation": "deschedule",
                  "renditions": {}
              }
          }
      }
      """
      When we get "/archive/123"
      Then we get existing resource
      """
      {
          "_id": "123",
          "guid": "123",
          "state": "in_progress",
          "operation": "deschedule",
          "associations": {
              "media--1": {
                  "guid": "234",
                  "type": "picture",
                  "state": "in_progress",
                  "operation": "deschedule"
              }
          }
      }
      """
      When we get "/archive/234"
      Then we get existing resource
      """
      {
          "guid": "234",
          "type": "picture",
          "state": "in_progress",
          "operation": "deschedule"
      }
      """
      When we publish "123" with "publish" type and "published" state
      """
      {"publish_schedule": "#DATE+2#"}
      """
      Then we get OK response
      And we get existing resource
      """
      {
          "_id": "123",
          "guid": "123",
          "state": "scheduled",
          "operation": "publish",
          "associations": {
              "media--1": {
                  "_id": "234",
                  "type": "picture",
                  "state": "scheduled",
                  "operation": "publish"
              }
          }
      }
      """
      When we get "/archive/123"
      Then we get existing resource
      """
      {
          "_id": "123",
          "guid": "123",
          "state": "scheduled",
          "operation": "publish",
          "associations": {
              "media--1": {
                  "guid": "234",
                  "type": "picture",
                  "state": "scheduled",
                  "operation": "publish"
              }
          }
      }
      """
      When we get "/archive/234"
      Then we get existing resource
      """
      {
          "guid": "234",
          "type": "picture",
          "state": "scheduled",
          "operation": "publish"
      }
      """
      
    @auth
    Scenario: Send correction with adding a featuremedia
      Given config update
      """
      { "PUBLISH_ASSOCIATED_ITEMS": false}
      """
      And "vocabularies"
      """
      [{
        "_id": "crop_sizes",
        "unique_field": "name",
        "items": [
          {"is_active": true, "name": "original", "width": 800, "height": 600}
        ]
      }
      ]
      """
      And "validators"
      """
      [
          {"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
          {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
          {"_id": "publish_picture", "act": "publish", "type": "picture", "schema": {}},
          {"_id": "correct_picture", "act": "correct", "type": "picture", "schema": {}}
      ]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [
          {
            "guid": "123",
            "type": "text",
            "headline": "test",
            "state": "in_progress",
            "task": {
              "desk": "#desks._id#",
              "stage": "#desks.incoming_stage#",
              "user": "#CONTEXT_USER_ID#"
              },
            "subject":
              [
                {"qcode": "17004000",
                "name": "Statistics"}
              ],
            "body_html": "Test Document body",
            "_current_version": 1
          },
          {
              "guid": "234",
              "type": "picture",
              "slugline": "234",
              "headline": "234",
              "state": "in_progress",
              "task": {
                "desk": "#desks._id#",
                "stage": "#desks.incoming_stage#",
                "user": "#CONTEXT_USER_ID#"
              },
              "renditions": {
                  "original": {"CropLeft": 0, "CropRight": 800, "CropTop": 0, "CropBottom": 600}
              },
              "_current_version": 1
          }
      ]
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
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {
        "_current_version": 2,
        "type": "text",
        "state": "published",
        "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}
      }
      """
      When we publish "123" with "correct" type and "corrected" state
      """
      {
        "associations": {
          "featuremedia": {
              "_id": "234",
              "type": "picture",
              "guid": "234",
              "byline": "foo",
              "alt_text": "alt_text",
              "description_text": "description_text",
              "headline": "234",
              "renditions": {
                    "original": {"CropLeft": 0, "CropRight": 800, "CropTop": 0, "CropBottom": 600}
                  }
              }
          }
      }
      """
      Then we get OK response
      And we get existing resource
      """
      {
        "_current_version": 3,
        "state": "corrected",
        "associations": {
            "featuremedia": {
              "_id": "234",
              "type": "picture",
              "guid": "234",
              "byline": "foo",
              "alt_text": "alt_text",
              "description_text": "description_text",
              "headline": "234",
              "renditions": {
                    "original": {"CropLeft": 0, "CropRight": 800, "CropTop": 0, "CropBottom": 600}
                  }
              }
          }
      }
      """

    @auth
    Scenario: Publish a user content from personal space
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
      When we post to "/archive" with success
      """
      [{"guid": "123", "type": "text", "headline": "test", "state": "in_progress",
        "task": {"user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body",
        "dateline": {
          "located" : {
              "country" : "Afghanistan",
              "tz" : "Asia/Kabul",
              "city" : "Mazar-e Sharif",
              "alt_name" : "",
              "country_code" : "AF",
              "city_code" : "Mazar-e Sharif",
              "dateline" : "city",
              "state" : "Balkh",
              "state_code" : "AF.30"
          },
          "text" : "MAZAR-E SHARIF, Dec 30  -",
          "source": "AAP"}
        }]
      """
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 1, "state": "in_progress"}
      """
      Then we get OK response
      When we publish "#archive._id#?desk_id=#desks._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {
        "_current_version": 2,
        "type": "text",
        "state": "published",
        "task":{"desk": "#desks._id#", "user": "#CONTEXT_USER_ID#"}
       }
      """
