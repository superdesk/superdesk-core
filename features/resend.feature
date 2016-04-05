Feature: Resend

  @auth
  Scenario: Resend an unpublished story fails
    Given "desks"
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
    When we post to "/archive/#archive._id#/resend"
    """
    {
      "subscribers": [1],
      "version": 2
    }
    """
    Then we get error 400
    """
    {"_message": "Only published, corrected or killed stories can be resent!"}
    """

  @auth
  Scenario: Resend a previous version of a published story fails
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
    [{"guid": "123", "headline": "test", "_current_version": 3, "state": "fetched",
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

    When we post to "/archive/#archive._id#/resend"
    """
    {
      "subscribers": ["#subscribers._id#"],
      "version": 2
    }
    """
    Then we get error 400
    """
    {"_message": "Please use the newest version 4 to resend!"}
    """

  @auth
  Scenario: Resend a published version of a corrected story fails
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
    [{"guid": "123", "headline": "test", "_current_version": 3, "state": "fetched",
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
    When we publish "#archive._id#" with "correct" type and "corrected" state
    """
    {"headline": "corrected"}
    """
    Then we get OK response
    When we enqueue published

    When we post to "/archive/#archive._id#/resend"
    """
    {
      "subscribers": ["#subscribers._id#"],
      "version": 4
    }
    """
    Then we get error 400
    """
    {"_message": "Please use the newest version 5 to resend!"}
    """


  @auth
  Scenario: Resend a updated story fails
    Given the "validators"
    """
    [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
    """
    And "desks"
    """
    [{"name": "Sports", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
    """
    And "archive"
    """
    [{"guid": "123", "headline": "test", "_current_version": 3, "state": "fetched",
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
    When we rewrite "123"
    """
    {"desk_id": "#desks._id#"}
    """
    When we get "/published"
    Then we get existing resource
    """
    {"_items" : [{"_id": "123", "rewritten_by": "#REWRITE_ID#"}]}
    """
    When we get "/archive/123"
    Then we get existing resource
    """
    {"_id": "123", "rewritten_by": "#REWRITE_ID#"}
    """

    When we post to "/archive/#archive._id#/resend"
    """
    {
      "subscribers": ["#subscribers._id#"],
      "version": 4
    }
    """
    Then we get error 400
    """
    {"_message": "Updated story cannot be resent!"}
    """

  @auth
  @vocabulary
  Scenario: Resend a published story
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
    [{"guid": "123", "headline": "test", "_current_version": 3, "state": "fetched",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "slugline": "test",
      "body_html": "Test Document body"}]
    """
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
    And "subscribers"
      """
      [{
        "_id": "sub-1",
        "name":"Channel 3",
        "media_type":"media",
        "subscriber_type": "wire",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "email": "test@test.com",
        "products": ["570340ef1d41c89b50716dad"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      ]
      """
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 1 items
    """
    {
      "_items": [
        {"state": "pending", "content_type": "text",
        "subscriber_id": "sub-1", "item_id": "123", "item_version": 4}
      ]
    }
    """
    When we post to "/subscribers"
    """
    {
        "name":"Channel 10",
        "media_type":"media",
        "subscriber_type": "wire",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "email": "test@test.com",
        "products": ["570340ef1d41c89b50716dad"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
    """

    When we post to "/archive/#archive._id#/resend"
    """
    {
      "subscribers": ["#subscribers._id#"],
      "version": 4
    }
    """
    Then we get OK response
    When we get "/publish_queue"
    Then we get list with 2 items
    """
    {
      "_items": [
        {"state": "pending", "content_type": "text",
        "subscriber_id": "#subscribers._id#", "item_id": "123", "item_version": 4}
      ]
    }
    """

  @auth
  @vocabulary
  Scenario: Resend a published text story to a digital subscriber
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
    [{"guid": "123", "headline": "test", "_current_version": 3, "state": "fetched",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "slugline": "test",
      "body_html": "Test Document body"}]
    """
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
    And "subscribers"
      """
      [{
        "_id": "sub-1",
        "name":"Channel 3",
        "media_type":"media",
        "subscriber_type": "wire",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "email": "test@test.com",
        "products": ["570340ef1d41c89b50716dad"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      ]
      """
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 1 items
    """
    {
      "_items": [
        {"state": "pending", "content_type": "text",
        "subscriber_id": "sub-1", "item_id": "123", "item_version": 4}
      ]
    }
    """
    When we post to "/subscribers"
    """
    {
        "name":"Channel 10",
        "media_type":"media",
        "subscriber_type": "digital",
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "email": "test@test.com",
        "products": ["570340ef1d41c89b50716dad"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
    """

    When we post to "/archive/#archive._id#/resend"
    """
    {
      "subscribers": ["#subscribers._id#"],
      "version": 4
    }
    """
    Then we get OK response
    When we get "/publish_queue"
    Then we get list with 2 items
    """
    {
      "_items": [
        {"state": "pending", "content_type": "composite",
        "subscriber_id": "#subscribers._id#", "item_version": 2}
      ]
    }
    """