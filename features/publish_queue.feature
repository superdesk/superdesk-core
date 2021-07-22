Feature: Publish Queue

  @auth
  Scenario: Add a new transmission entry to the queue
    Given empty "archive"
    And empty "subscribers"
    When we post to "/archive"
    """
    [{"headline": "test"}]
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
    And we post to "/publish_queue" with success
    """
    {
       "item_id":"#archive._id#","publish_schedule": "2016-05-30T10:00:00+00:00", "subscriber_id":"#subscribers._id#",
       "destination":{"name":"Test","format": "nitf","delivery_type":"email","config":{"recipients":"test@test.com"}}
    }
    """
    And we get "/publish_queue"
    Then we get list with 1 items
    """
    {
      "_items":
        [
          {"destination":{"name":"Test"}}
        ]
    }
    """


  @auth
  Scenario: No transmission will happen if subscriber doesn't have product
    Given empty "archive"
    And empty "subscribers"
    And empty "products"
    And "products"
      """
      [{
        "_id":"570340ef1d41c89b50716dad", "name":"prod-1","codes":"abc"
      },
      {
        "_id":"570340ef1d41c89b50716dae", "name":"prod-2","codes":"def,xyz"
      },
      {
        "_id":"570340ef1d41c89b50716daf", "name":"prod-3"
      }]
      """
    And the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
       {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
       {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
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
    And "subscribers"
      """
      [{
        "name":"Channel 3",
        "media_type":"media",
        "subscriber_type": "digital",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "email": "test@test.com",
        "codes": "ptr, axx,",
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }]
      """

    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response

    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 0 items


  @auth @vocabulary
  Scenario: Error in queueing will be recorded if happens
    Given empty "archive"
    And empty "subscribers"
    And empty "products"
    Given empty "filter_conditions"

    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "place", "operator": "match", "value": "4"}]
    """
    Then we get latest

    Given empty "content_filters"
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer"}]
    """
    Then we get latest
    Given "products"
      """
      [{
        "_id":"570340ef1d41c89b50716dae", "name":"prod-2","codes":"def,xyz",
        "content_filter": {
            "filter_id": "#content_filter._id#",
            "filter_type": "blocking"
        },
        "geo_restrictions": "NSW"
      }]
      """
    And the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
      """
    And "desks"
      """
      [{"name": "Sports"}]
      """
    And "archive"
      """
      [{"guid": "123",
        "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "target_regions": [{"a": "b"}]
      }]
      """
    And "subscribers"
      """
      [{
        "name":"Channel 3",
        "media_type":"media",
        "subscriber_type": "wire",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "email": "test@test.com",
        "products": ["570340ef1d41c89b50716dae"],
        "codes": "ptr, axx,",
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }]
      """

    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response

    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 0 items
    When we get "/published"
    Then we get existing resource
    """
    {
        "_items": [
            {
                "type": "text",
                "queue_state": "error",
                "error_message": "400: Key is missing on article to be published: 'qcode'"
            }
        ]
    }
    """


  @auth
  Scenario: Transmission will have the collated codes
    Given empty "archive"
    And empty "subscribers"
    And empty "products"
    And "products"
      """
      [{
        "_id":"570340ef1d41c89b50716dad", "name":"prod-1","codes":"abc"
      },
      {
        "_id":"570340ef1d41c89b50716dae", "name":"prod-2","codes":"def,xyz"
      },
      {
        "_id":"570340ef1d41c89b50716daf", "name":"prod-3"
      }]
      """
    And the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
       {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
       {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
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
    And "subscribers"
      """
      [{
        "name":"Channel 3",
        "media_type":"media",
        "subscriber_type": "digital",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "email": "test@test.com",
        "codes": "ptr, axx,",
        "products": ["570340ef1d41c89b50716dad", "570340ef1d41c89b50716dae", "570340ef1d41c89b50716daf"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }]
      """

    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response

    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 1 items
    """
    {
      "_items": [
        {
          "state": "pending",
          "content_type": "text",
          "subscriber_id": "#subscribers._id#",
          "item_id": "123",
          "item_version": 2,
          "codes": ["abc", "xyz", "def", "ptr", "axx"]
        }
      ]
    }
    """
    When we publish "#archive._id#" with "correct" type and "corrected" state
    """
    {"body_html": "Corrected", "slugline": "corrected", "headline": "corrected"}
    """
    Then we get OK response
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 2 items
    """
    {
      "_items": [
        {
          "headline": "corrected",
          "codes": ["abc", "xyz", "def"]
        }
      ]
    }
    """
    When we publish "#archive._id#" with "kill" type and "killed" state
    Then we get OK response
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 3 items
    """
    {
      "_items": [
        {
          "publishing_action": "killed",
          "codes": ["abc", "xyz", "def"]
        }
      ]
    }
    """

  @auth
  Scenario: Patch a transmission entry
    Given empty "archive"
    And empty "subscribers"
    When we post to "/archive"
    """
    [{"headline": "test"}]
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
      "destinations":[{"name":"destination2","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
    }
    """
    And we post to "/publish_queue" with success
    """
    {
      "item_id":"#archive._id#","subscriber_id":"#subscribers._id#",
      "destination":{"name":"destination2","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}
    }
    """
    And we get "/publish_queue"
    Then we get list with 1 items
    """
    {
      "_items":
        [
          {"state":"pending"}
        ]
    }
    """
    When we patch "/publish_queue/#publish_queue._id#"
    """
    {
      "state": "in-progress"
    }
    """
    And we get "/publish_queue"
    Then we get list with 1 items
    """
    {
      "_items":
        [
          {"state":"in-progress"}
        ]
    }
    """

  @auth
  Scenario: Published Item should have published sequence number when published and placed in queue
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
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"destination2","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we post to "/archive" with success
      """
      [{"guid": "123", "headline": "test", "body_html": "body", "state": "fetched",
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
      """
      And we post to "/stages" with success
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
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get "publish_sequence_no" in "/published/123"

  @auth @notification
  Scenario: Creating a new publish queue entry should add published sequence number
    Given empty "archive"
    And empty "subscribers"
    When we post to "/archive"
    """
    [{"headline": "test"}]
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
      "destinations":[{"name":"destination2","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
    }
    """
    And we post to "/publish_queue"
    """
    {
       "item_id":"#archive._id#","publish_schedule": "2016-05-30T10:00:00+00:00", "subscriber_id":"#subscribers._id#",
       "destination":{"name":"destination2","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}
    }
    """
    Then we get "published_seq_num" in "/publish_queue/#archive._id#"
    When we patch "/publish_queue/#publish_queue._id#"
    """
    {"state": "success"}
    """
    Then we get latest
    """
    {"state": "success"}
    """
    And we get notifications
    """
    [{"event": "publish_queue:update", "extra": {"queue_id": "#publish_queue._id#", "state": "success"}}]
    """

  @auth
  Scenario: publish queue us returned in correct order
    Given "publish_queue"
    """
    [
      {"_created":"2016-05-30T13:00:00+00:00", "subscriber_id": 4, "published_seq_num": 2},
      {"_created":"2016-05-30T12:00:00+00:00", "subscriber_id": 4, "published_seq_num": 3},
      {"_created":"2016-05-30T11:00:00+00:00", "subscriber_id": 3, "published_seq_num": 1},
      {"_created":"2016-05-30T10:00:00+00:00", "subscriber_id": 2, "published_seq_num": 1}
    ]
    """
    When we get "/publish_queue"
    Then we get list ordered by _created with 4 items

  @auth
  Scenario: Expire published queue items
    Given empty "subscribers"
    And config update
    """
    {"PUBLISH_QUEUE_EXPIRY_MINUTES": -1}
    """
    When we post to "/archive" with success
    """
    [{"guid": "123", "headline": "test"}]
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
    And we post to "/publish_queue" with success
    """
    {
       "item_id":"#archive._id#","publish_schedule": "2016-05-30T10:00:00+00:00", "subscriber_id":"#subscribers._id#",
       "destination":{"name":"Test","format": "nitf","delivery_type":"email","config":{"recipients":"test@test.com"}}
    }
    """
    And we get "/publish_queue"
    Then we get list with 1 items
    """
    {
      "_items":
        [
          {"destination":{"name":"Test"}}
        ]
    }
    """
    When we expire items
    """
    []
    """
    And we get "/publish_queue"
    Then we get list with 0 items


  @auth
  Scenario: Transmission will have the collated codes on takedown
    Given empty "archive"
    And empty "subscribers"
    And empty "products"
    And "products"
      """
      [{
        "_id":"570340ef1d41c89b50716dad", "name":"prod-1","codes":"abc"
      },
      {
        "_id":"570340ef1d41c89b50716dae", "name":"prod-2","codes":"def,xyz"
      },
      {
        "_id":"570340ef1d41c89b50716daf", "name":"prod-3"
      }]
      """
    And the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
       {"_id": "correct_text", "act": "correct", "type": "text", "schema":{}},
       {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
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
    And "subscribers"
      """
      [{
        "name":"Channel 3",
        "media_type":"media",
        "subscriber_type": "digital",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "email": "test@test.com",
        "codes": "ptr, axx,",
        "products": ["570340ef1d41c89b50716dad", "570340ef1d41c89b50716dae", "570340ef1d41c89b50716daf"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }]
      """

    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response

    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 1 items
    """
    {
      "_items": [
        {
          "state": "pending",
          "content_type": "text",
          "subscriber_id": "#subscribers._id#",
          "item_id": "123",
          "item_version": 2,
          "codes": ["abc", "xyz", "def", "ptr", "axx"]
        }
      ]
    }
    """
    When we publish "#archive._id#" with "correct" type and "corrected" state
    """
    {"body_html": "Corrected", "slugline": "corrected", "headline": "corrected"}
    """
    Then we get OK response
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 2 items
    """
    {
      "_items": [
        {
          "headline": "corrected",
          "codes": ["abc", "xyz", "def"]
        }
      ]
    }
    """
    When we publish "#archive._id#" with "takedown" type and "recalled" state
    Then we get OK response
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 3 items
    """
    {
      "_items": [
        {
          "publishing_action": "recalled",
          "codes": ["abc", "xyz", "def"]
        }
      ]
    }
    """