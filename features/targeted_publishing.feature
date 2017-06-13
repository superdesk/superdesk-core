Feature: Targeted Publishing

  Background: Setup data
    Given "desks"
    """
    [{"name": "Sports", "content_expiry": 60, "members": [{"user": "#CONTEXT_USER_ID#"}]}]
    """
    And "validators"
    """
    [{"schema": {}, "type": "text", "act": "publish", "_id": "publish_text"},
     {"schema": {}, "type": "text", "act": "correct", "_id": "correct_text"},
     {"schema": {}, "type": "text", "act": "kill", "_id": "kill_text"}]
    """
    And "products"
    """
    [{"_id": "1", "name":"prod-1", "codes":"abc,xyz"},
     {"_id": "2", "name":"prod-2", "codes":"klm", "geo_restrictions": "VIC"},
     {"_id": "3", "name":"prod-3", "codes":"klm", "geo_restrictions": "QLD"},
     {"_id": "4", "name":"prod-4", "codes":"abc,xyz,klm"}]
    """
    And "subscribers"
    """
    [{
      "_id": "sub-1",
      "name":"Channel 1",
      "media_type": "media",
      "subscriber_type": "digital",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["1", "4"],
      "codes": "Aaa",
      "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
    },
    {
      "_id": "sub-2",
      "name":"Wire channel with geo restriction Victoria",
      "media_type":"media",
      "subscriber_type": "wire",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["2"],
      "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
    },
    {
      "_id": "sub-3",
      "name":"Wire channel without geo restriction",
      "media_type":"media",
      "subscriber_type": "wire",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["1"],
      "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
    },
    {
      "_id": "sub-4",
      "name":"Wire channel with geo restriction Queensland",
      "media_type":"media",
      "subscriber_type": "wire",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["3"],
      "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
    },
    {
      "_id": "sub-5",
      "name":"Wire channel with geo restriction no product",
      "media_type":"media",
      "subscriber_type": "wire",
      "codes": "ptk,rst",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
    },
    {
      "_id": "sub-2-api",
      "name":"Wire channel with geo restriction Victoria API",
      "media_type":"media",
      "subscriber_type": "wire",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "api_products": ["2"]
    },
    {
      "_id": "sub-4-api",
      "name":"Wire channel with geo restriction Queensland API",
      "media_type":"media",
      "subscriber_type": "wire",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "api_products": ["3"]
    }
    ]
    """
    When we post to "content_templates"
    """
    {"template_name": "kill", "template_type": "kill",
     "data": {"body_html": "<p>Please kill story slugged {{ item.slugline }} ex {{ item.dateline['text'] }}.<\/p>",
              "type": "text", "abstract": "This article has been removed", "headline": "Kill\/Takedown notice ~~~ Kill\/Takedown notice",
              "urgency": 1, "priority": 1,  "anpa_take_key": "KILL\/TAKEDOWN"}
    }
    """

  @auth @notification
  Scenario: Publish a story to a target region
    When we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "state": "fetched", "slugline": "slugline",
      "headline": "headline",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "target_regions": [{"qcode": "QLD", "name": "Queensland", "allow": true}],
      "body_html": "Test Document body"}]
    """
    Then we get OK response
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" :
      [{"_id": "123", "state": "published", "type": "text", "_current_version": 2}]}
    """
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 2 items
    """
    {
      "_items":
        [
          {"subscriber_id": "sub-4"},
          {"subscriber_id": "sub-4-api"}
        ]
    }
    """
    When we get "/items/123"
    Then we get OK response
    Then we assert the content api item "123" is not published to subscriber "sub-4"
    Then we assert the content api item "123" is published to subscriber "sub-4-api"

  @auth @notification
  Scenario: Publish a story to a target region with negation
    When we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "state": "fetched", "slugline": "slugline",
      "headline": "headline",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "target_regions": [{"qcode": "NSW", "name": "New South Wales", "allow": false}],
      "body_html": "Test Document body"}]
    """
    Then we get OK response
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [{"_id": "123", "state": "published", "type": "text", "_current_version": 2}]}
    """
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 4 items
    """
    {
      "_items":
        [
          {"subscriber_id": "sub-2"},
          {"subscriber_id": "sub-2-api"},
          {"subscriber_id": "sub-4"},
          {"subscriber_id": "sub-4-api"}
        ]
    }
    """
    When we get "/items/123"
    Then we get OK response
    Then we assert the content api item "123" is not published to subscriber "sub-4"
    Then we assert the content api item "123" is not published to subscriber "sub-2"
    Then we assert the content api item "123" is not published to subscriber "sub-1"
    Then we assert the content api item "123" is not published to subscriber "sub-3"
    Then we assert the content api item "123" is not published to subscriber "sub-5"
    Then we assert the content api item "123" is published to subscriber "sub-4-api"
    Then we assert the content api item "123" is published to subscriber "sub-2-api"

  @auth @notification
  Scenario: Publish a story to a target region doesn't publish if no product
    When we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "state": "fetched", "slugline": "slugline",
      "headline": "headline",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "target_regions": [{"qcode": "NSW", "name": "New South Wales", "allow": true}],
      "body_html": "Test Document body"}]
    """
    Then we get OK response
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [{"_id": "123", "state": "published", "type": "text", "_current_version": 2}]}
    """
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 0 items
    When we get "/items/123"
    Then we get OK response
    Then we assert the content api item "123" is not published to any subscribers


  @auth @notification
  Scenario: Publish a story normally doesn't publish if product has target region
    When we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "state": "fetched", "slugline": "slugline",
      "headline": "headline",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body"}]
    """
    Then we get OK response
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [{"_id": "123", "state": "published", "type": "text", "_current_version": 2}]}
    """
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 2 items
    """
    {
      "_items":
        [
          {"subscriber_id": "sub-1"},
          {"subscriber_id": "sub-3"}
        ]
    }
    """
    When we get "/items/123"
    Then we get OK response
    Then we assert the content api item "123" is not published to any subscribers


  @auth @notification
  Scenario: Publish a story to a target subscriber type
    When we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "state": "fetched", "slugline": "slugline",
      "headline": "headline",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "target_types": [{"qcode":"digital", "name": "digital", "allow": true}],
      "body_html": "Test Document body"}]
    """
    Then we get OK response
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [{"_id": "123", "state": "published", "type": "text", "_current_version": 2}]}
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
    When we get "/items/123"
    Then we get OK response
    Then we assert the content api item "123" is not published to any subscribers

  @auth @notification
  Scenario: Publish a story to target subscribers even no products
    When we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "state": "fetched", "slugline": "slugline",
      "headline": "headline",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "target_subscribers": [{"_id": "sub-1"}, {"_id": "sub-4"}, {"_id": "sub-5"}],
      "body_html": "Test Document body"}]
    """
    Then we get OK response
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [{"_id": "123", "state": "published", "type": "text", "_current_version": 2}]}
    """
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 3 items
    """
    {
      "_items":
        [
          {"subscriber_id": "sub-1", "codes": ["Aaa", "abc", "xyz"]},
          {"subscriber_id": "sub-4"},
          {"subscriber_id": "sub-5", "codes": ["ptk", "rst"]}
        ]
    }
    """
    When we get "/items/123"
    Then we get OK response
    Then we assert the content api item "123" is not published to any subscribers

  @auth @notification
  Scenario: Publish a story to target subscribers and region
    When we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "state": "fetched", "slugline": "slugline",
      "headline": "headline",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "target_regions": [{"qcode": "QLD", "name": "Queensland", "allow": true}],
      "target_subscribers": [{"_id": "sub-3"}],
      "body_html": "Test Document body"}]
    """
    Then we get OK response
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [{"_id": "123", "state": "published", "type": "text", "_current_version": 2}]}
    """
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 3 items
    """
    {
      "_items":
        [
          {"subscriber_id": "sub-3"},
          {"subscriber_id": "sub-4"},
          {"subscriber_id": "sub-4-api"}
        ]
    }
    """
    When we get "/items/123"
    Then we get OK response
    Then we assert the content api item "123" is published to subscriber "sub-4-api"
    Then we assert the content api item "123" is not published to subscriber "sub-4"
    Then we assert the content api item "123" is not published to subscriber "sub-3"

  @auth @notification
  Scenario: Correct a targeted story with a added target ignores the change
    When we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "state": "fetched", "slugline": "slugline",
      "headline": "headline",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "target_subscribers": [{"_id": "sub-1"}, {"_id": "sub-4"}, {"_id": "sub-5"}],
      "body_html": "Test Document body"}]
    """
    Then we get OK response
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [{"_id": "123", "state": "published", "type": "text", "_current_version": 2}]}
    """
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 3 items
    """
    {
      "_items":
        [
          {"subscriber_id": "sub-1", "codes": ["Aaa", "abc", "xyz"]},
          {"subscriber_id": "sub-4"},
          {"subscriber_id": "sub-5", "codes": ["ptk", "rst"]}
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
    Then we get list with 6 items
    """
    {
      "_items":
        [
          {"subscriber_id": "sub-1", "codes": ["Aaa", "abc", "xyz"],
          "publishing_action": "corrected", "headline": "corrected"},
          {"subscriber_id": "sub-4", "headline": "corrected", "publishing_action": "corrected"},
          {"subscriber_id": "sub-5", "codes": ["ptk", "rst"],
          "publishing_action": "corrected", "headline": "corrected"}
        ]
    }
    """
    When we publish "#archive._id#" with "correct" type and "corrected" state
    """
    {"target_subscribers": [{"_id": "sub-2"}], "headline": "corrected2"}
    """
    Then we get OK response
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 10 items
    """
    {
      "_items":
        [
          {"subscriber_id": "sub-1", "codes": ["Aaa", "abc", "xyz", "klm"], "headline": "corrected2"},
          {"subscriber_id": "sub-4", "headline": "corrected"},
          {"subscriber_id": "sub-5", "codes": ["ptk", "rst"], "headline": "corrected2"}
        ]
    }
    """
