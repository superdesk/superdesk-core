Feature: Edit scheduled but not published item

  Background: Setup data required to test the Embargo feature
    Given the "validators"
    """
    [{"schema": {}, "type": "text", "act": "publish", "_id": "publish_text"},
     {"schema": {}, "type": "text", "act": "correct", "_id": "correct_text"},
     {"schema": {}, "type": "text", "act": "kill",    "_id": "kill_text"}]
    """
    And "desks"
    """
    [{"name": "Sports", "content_expiry": "4320"}]
    """
    And "products"
      """
      [{
        "_id": "1", "name":"prod-1", "codes":"abc,xyz"
      }]
      """
    And "subscribers"
    """
    [{"_id": "123",
      "name":"Wire Subscriber",
      "media_type":"media",
      "subscriber_type": "wire",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["1"],
      "destinations":[{"name":"email","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]},
     {"_id": "321",
      "name":"Digital Subscriber",
      "media_type":"media",
      "subscriber_type": "digital",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["1"],
      "destinations":[{"name":"email","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]},
     {"_id": "456",
      "name":"2nd Wire Subscriber",
      "media_type":"non-media",
      "subscriber_type": "wire",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["1"],
      "destinations":[{"name":"email","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]}
    ]
    """
    And "archive"
    """
    [{"guid": "123", "type": "text", "slugline": "text with embargo", "headline": "test", "_current_version": 1, "state": "fetched", "anpa_take_key": "Take",
      "unique_id": "123456", "unique_name": "#text_with_embargo", "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
    """

  @auth
  Scenario: Edit an scheduled item
    When we patch "/archive/123"
    """
    {"publish_schedule": "#DATE+1#"}
    """
    Then we get response code 200
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    And we get existing resource
    """
    {"state": "scheduled", "_id": "123"}
    """
    When we get "/archive/#archive.123.take_package#"
    Then we get existing resource
    """
    {"state": "scheduled", "_id": "#archive.123.take_package#"}
    """
    When we get "/published"
    Then we get list with 2 items
    """
    {"_items": [
      {"state": "scheduled", "_id": "123", "type": "text"},
      {"state": "scheduled", "_id": "#archive.123.take_package#", "type": "composite"}
    ]}
    """
    When we patch "/archive/123"
    """
    {"slugline": "changed slugline"}
    """
    Then we get OK response

    When we get "/published"
    Then we get list with 2 items
    """
    {"_items": [
      {"state": "scheduled", "_id": "123", "type": "text", "slugline": "changed slugline"},
      {"state": "scheduled", "type": "composite", "slugline": "changed slugline"}
    ]}
    """
    
  @auth
  Scenario: Spike an scheduled item
    When we patch "/archive/123"
    """
    {"publish_schedule": "#DATE+1#"}
    """
    Then we get response code 200
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    And we get existing resource
    """
    {"state": "scheduled", "_id": "123"}
    """
    When we get "/archive/#archive.123.take_package#"
    Then we get existing resource
    """
    {"state": "scheduled", "_id": "#archive.123.take_package#"}
    """
    When we get "/published"
    Then we get list with 2 items
    """
    {"_items": [
      {"state": "scheduled", "_id": "123", "type": "text"},
      {"state": "scheduled", "_id": "#archive.123.take_package#", "type": "composite"}
    ]}
    """
    When we spike "123"
    Then we get OK response
    When we expire items
    """
    ["123"]
    """
    When we get "/published"
    Then we get list with 0 items
    
  @auth
  Scenario: Republish an scheduled item
    When we patch "/archive/123"
    """
    {"publish_schedule": "#DATE+1#"}
    """
    Then we get response code 200
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    And we get existing resource
    """
    {"state": "scheduled", "_id": "123"}
    """
    When we get "/archive/#archive.123.take_package#"
    Then we get existing resource
    """
    {"state": "scheduled", "_id": "#archive.123.take_package#"}
    """
    When we get "/published"
    Then we get list with 2 items
    """
    {"_items": [
      {"state": "scheduled", "_id": "123", "type": "text"},
      {"state": "scheduled", "_id": "#archive.123.take_package#", "type": "composite"}
    ]}
    """
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    And we get existing resource
    """
    {"state": "scheduled", "_id": "123"}
    """
    When we get "/published"
    Then we get list with 2 items
    """
    {"_items": [
      {"state": "scheduled", "_id": "123", "type": "text"},
      {"state": "scheduled", "_id": "#archive.123.take_package#", "type": "composite"}
    ]}
