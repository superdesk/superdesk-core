Feature: Archive history

    @auth @notification
    Scenario: History of duplicated stories
      Given "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{  "type":"text", "event_id": "abc123", "headline": "test1", "guid": "123",
          "original_creator": "#CONTEXT_USER_ID#",
          "state": "submitted", "source": "REUTERS", "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
      """
      When we patch given
      """
      {"headline": "test2"}
      """
      And we patch latest
      """
      {"headline": "test3"}
      """
      Then we get updated response
      """
      {"headline": "test3", "state": "in_progress", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
      """
      And we get version 3
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 3 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "update"},
        {"version": 3, "operation": "update"}
      ]}
      """
      When we post to "/archive/123/duplicate"
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 4 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "update"},
        {"version": 3, "operation": "update"},
        {"version": 3, "operation": "duplicate"}
      ]}
      """
      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      {"state": "submitted", "_current_version": 4, "source": "AAP",
       "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#", "user": "#CONTEXT_USER_ID#"},
       "original_id": "123"}
      """
      When we get "/archive_history?where=item_id==%22#duplicate._id#%22"
      Then we get list with 4 items
      """
      {"_items": [
        {"version": 1, "operation": "create", "original_item_id": "123"},
        {"version": 2, "operation": "update", "original_item_id": "123"},
        {"version": 3, "operation": "update", "original_item_id": "123"},
        {"version": 4, "operation": "duplicated_from"}
      ]}
      """

    @auth
    Scenario: History of rewrite activities
      Given "desks"
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
      When we rewrite "123"
      """
      {"desk_id": "#desks._id#"}
      """
      Then we get OK response
      When we get "/archive/#REWRITE_ID#"
      Then we get OK response
      When we get "/archive"
      Then we get existing resource
      """
      {"_items" : [{"_id": "#REWRITE_ID#", "anpa_take_key": "update", "rewrite_of": "123"}]}
      """
      When we get "/archive/123"
      Then we get existing resource
      """
      {"_id": "123", "rewritten_by": "#REWRITE_ID#", "place": [{"qcode" : "ACT"}]}
      """
      When we get "/archive_history?where=item_id==%22#REWRITE_ID#%22"
      Then we get list with 2 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 1, "operation": "link"}
      ]}
      """
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 2 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 1, "operation": "rewrite"}
      ]}
      """
      When we spike "#REWRITE_ID#"
      Then we get OK response
      When we get "/archive_history?where=item_id==%22#REWRITE_ID#%22"
      Then we get list with 3 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 1, "operation": "link"},
        {"version": 2, "operation": "spike"}
      ]}
      """
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 3 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 1, "operation": "rewrite"},
        {"version": 1, "operation": "unlink"}
      ]}
      """
      When we unspike "#REWRITE_ID#"
      When we get "/archive_history?where=item_id==%22#REWRITE_ID#%22"
      Then we get list with 4 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 1, "operation": "link"},
        {"version": 2, "operation": "spike"},
        {"version": 3, "operation": "unspike"}
      ]}
      """
      When we rewrite "123"
      """
      {"update": {"_id": "#REWRITE_ID#", "type": "text", "headline": "test",
      "_current_version": 3, "state": "submitted", "priority": 2}}
      """
      When we get "/archive_history?where=item_id==%22#REWRITE_ID#%22"
      Then we get list with 5 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 1, "operation": "link"},
        {"version": 2, "operation": "spike"},
        {"version": 3, "operation": "unspike"},
        {"version": 3, "operation": "link"}
      ]}
      """
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 4 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 1, "operation": "rewrite"},
        {"version": 1, "operation": "unlink"},
        {"version": 1, "operation": "rewrite"}
      ]}
      """


    @auth
    Scenario: History of publish activities
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
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 2 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "publish"}
      ]}
      """
      When we enqueue published
      When we get "/legal_archive/123"
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "published"}
      """
      When we get "/legal_archive_history?where=item_id==%22123%22"
      Then we get list with 2 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "publish"}
      ]}
      """
      When we publish "#archive._id#" with "correct" type and "corrected" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "corrected", "operation": "correct", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 3 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "publish"},
        {"version": 3, "operation": "correct"}
      ]}
      """
      When we enqueue published
      When we get "/legal_archive/123"
      Then we get OK response
      When we get "/legal_archive_history?where=item_id==%22123%22"
      Then we get list with 3 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "publish"},
        {"version": 3, "operation": "correct"}
      ]}
      """
      When we publish "#archive._id#" with "kill" type and "killed" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 4, "state": "killed", "operation": "kill", "pubstatus": "canceled", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 4 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "publish"},
        {"version": 3, "operation": "correct"},
        {"version": 4, "operation": "kill"}
      ]}
      """
      When we enqueue published
      When we get "/legal_archive/123"
      Then we get OK response
      When we get "/legal_archive_history?where=item_id==%22123%22"
      Then we get list with 4 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "publish"},
        {"version": 3, "operation": "correct"},
        {"version": 4, "operation": "kill"}
      ]}
      """



    @auth
    @provider
    Scenario: History of fetched story
      Given empty "archive"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And ingest from "reuters"
      """
      [{"guid": "tag_reuters.com_2014_newsml_LOVEA6M0L7U2E"}]
      """
      When we post to "/ingest/tag_reuters.com_2014_newsml_LOVEA6M0L7U2E/fetch"
      """
      {"desk": "#desks._id#"}
      """
      Then we get "_id"
      When we get "/archive_history?where=item_id==%22#_id#%22"
      Then we get list with 1 items
      """
      {"_items": [
        {"version": 1, "operation": "fetch"}
      ]}
      """
      When we post to "/archive/#_id#/lock"
      """
      {}
      """
      And we patch "/archive/#_id#"
      """
      {"headline": "test 2"}
      """
      Then we get existing resource
      """
      {"headline": "test 2", "state": "in_progress", "task": {"desk": "#desks._id#"}}
      """
      When we get "/archive_history?where=item_id==%22#_id#%22"
      Then we get list with 2 items
      """
      {"_items": [
        {"version": 1, "operation": "fetch"},
        {"version": 2, "operation": "update", "update":{"headline": "test 2"}}
      ]}
      """

    @auth
    Scenario: History of marking for highlights and desks
        Given "desks"
		"""
		[{"name": "desk1"}]
		"""
        When we post to "highlights"
        """
        {"name": "highlight1", "desks": ["#desks._id#"]}
        """
        Then we get new resource
        """
        {"name": "highlight1", "desks": ["#desks._id#"]}
        """
        When we post to "archive"
		"""
		[{"headline": "test"}]
		"""
        When we get "/archive_history?where=item_id==%22#archive._id#%22"
        Then we get list with 1 items
        """
        {"_items": [
          {"version": 1, "operation": "create"}
        ]}
        """
		When we post to "marked_for_highlights"
		"""
		[{"highlights": "#highlights._id#", "marked_item": "#archive._id#"}]
		"""
		Then we get new resource
        """
        {"highlights": "#highlights._id#", "marked_item": "#archive._id#"}
        """
        When we get "archive"
        Then we get list with 1 items
        """
        {"_items": [{"headline": "test", "highlights": ["#highlights._id#"],
                    "_updated": "#archive._updated#", "_etag": "#archive._etag#"}]}
        """
        When we get "/archive_history?where=item_id==%22#archive._id#%22"
        Then we get list with 2 items
        """
        {"_items": [
          {"version": 1, "operation": "create"},
          {"version": 1, "operation": "mark", "update":{"highlight_id":"#highlights._id#"}}
        ]}
        """
        When we post to "marked_for_highlights"
        """
        [{"highlights": "#highlights._id#", "marked_item": "#archive._id#"}]
        """
        And we get "archive"
        Then we get list with 1 items
        """
        {"_items": [{"highlights": [], "_updated": "#archive._updated#", "_etag": "#archive._etag#"}]}
        """
        When we get "/archive_history?where=item_id==%22#archive._id#%22"
        Then we get list with 3 items
        """
        {"_items": [
          {"version": 1, "operation": "create"},
          {"version": 1, "operation": "mark", "update":{"highlight_id":"#highlights._id#"}},
          {"version": 1, "operation": "unmark", "update":{"highlight_id":"#highlights._id#"}}
        ]}
        """
        When we post to "/marked_for_desks" with success
        """
        [{"marked_desk": "#desks._id#", "marked_item": "#archive._id#"}]
        """
        Then we get new resource
        """
        {"marked_desk": "#desks._id#", "marked_item": "#archive._id#"}
        """
        When we get "/archive_history?where=item_id==%22#archive._id#%22"
        Then we get list with 4 items
        """
        {"_items": [
          {"version": 1, "operation": "create"},
          {"version": 1, "operation": "mark", "update":{"highlight_id":"#highlights._id#"}},
          {"version": 1, "operation": "unmark", "update":{"highlight_id":"#highlights._id#"}},
          {"version": 1, "operation": "mark", "update":{"desk_id":"#desks._id#"}}
        ]}
        """
        When we post to "marked_for_desks"
        """
        [{"marked_desk": "#desks._id#", "marked_item": "#archive._id#"}]
        """
        And we get "archive"
        Then we get list with 1 items
        """
        {"_items": [{"marked_desks": []}]}
        """
        When we get "/archive_history?where=item_id==%22#archive._id#%22"
        Then we get list with 5 items
        """
        {"_items": [
          {"version": 1, "operation": "create"},
          {"version": 1, "operation": "mark", "update":{"highlight_id":"#highlights._id#"}},
          {"version": 1, "operation": "unmark", "update":{"highlight_id":"#highlights._id#"}},
          {"version": 1, "operation": "mark", "update":{"desk_id":"#desks._id#"}},
          {"version": 1, "operation": "unmark", "update":{"desk_id":"#desks._id#"}}
        ]}
        """

  @auth
  @vocabulary
  Scenario: History of resend
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
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 2 items
    """
    {"_items": [
      {"version": 3, "operation": "create"},
      {"version": 4, "operation": "publish"}
    ]}
    """
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
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 3 items
    """
    {"_items": [
      {"version": 3, "operation": "create"},
      {"version": 4, "operation": "publish"},
      {"version": 4, "operation": "resend", "update":{"subscribers":["#subscribers._id#"]}}
    ]}
    """

  @auth
  @vocabulary
  Scenario: History of schedule item
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
        "publish_schedule":"#DATE+2#",
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
      """
        {"publish_schedule": "#DATE+2#"}
      """
      Then we get OK response
      When we get "/legal_archive/123"
      Then we get error 404
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 2 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "publish", "update": {"state": "scheduled"}}
      ]}
      """
      When the publish schedule lapses
      """
      ["123"]
      """
      When we enqueue published
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 3 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "publish", "update": {"state": "scheduled"}},
        {"version": 3, "operation": "publish", "update": {"state": "published"}}
      ]}
      """
      When we get "/legal_archive/123"
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "published"}
      """
      When we get "/legal_archive_history?where=item_id==%22123%22"
      Then we get list with 3 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "publish", "update": {"state": "scheduled"}},
        {"version": 3, "operation": "publish", "update": {"state": "published"}}
      ]}
      """

  @auth
  @vocabulary
  Scenario: History of deschedule item
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
        "publish_schedule":"#DATE+2#",
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
      """
        {"publish_schedule": "#DATE+1#"}
      """
      Then we get OK response
      When we get "/legal_archive/123"
      Then we get error 404
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 2 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "publish", "update": {"state": "scheduled"}}
      ]}
      """
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
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 3 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "publish", "update": {"state": "scheduled"}},
        {"version": 3, "operation": "update", "update": {"operation": "deschedule"}}
      ]}
      """


    @auth
    @provider
    @vocabulary
    Scenario: History of the routed item
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
    And "users"
    """
    [{
        "username": "foo",
        "display_name": "foo",
        "email": "mock@mail.com.au",
        "is_active": true,
        "needs_activation": true
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
            "filter": null,
            "actions": {
              "fetch": [{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}],
              "publish": [],
              "exit": true
            }
          }
        ]
      }
    ]
    """
    Then we get response code 201
    When we ingest with routing scheme "email" "json-email.txt"
    """
    #routing_schemes._id#
    """
    When we get "/ingest"
    Then we get list with 1 items
    """
    {
        "_items": [
            {
                "headline": "Headline-2",
                "slugline": "Slugline-2",
                "original_creator": "#users._id#"
            }
        ]
    }
    """
    When we get "/archive"
    Then we get list with 1 items
    """
    {
        "_items": [
            {
                "headline": "Headline-2",
                "slugline": "Slugline-2",
                "original_creator": "#users._id#"
            }
        ]
    }
    """
    When we get "/archive_history"
    Then we get list with 2 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 1, "operation": "fetch"}
      ]}
      """

  @auth
  Scenario: History of item locks and unlocks
    Given "desks"
    """
    [{"name": "Sports", "members": [{"user": "#CONTEXT_USER_ID#"}]}]
    """
    And "archive"
    """
    [{  "type":"text", "event_id": "abc123", "headline": "test1", "guid": "123",
      "original_creator": "#CONTEXT_USER_ID#",
      "state": "submitted", "source": "REUTERS", "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
    """
    When we post to "/archive/#archive._id#/lock"
    """
    {"lock_action": "edit"}
    """
    Then we get OK response
    When we post to "/archive/#archive._id#/unlock"
    """
    {}
    """
    Then we get OK response
    When we get "/archive_history?where=item_id==%22#archive._id#%22"
    Then we get list with 3 items
    """
    {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 1, "operation": "item_lock", "update": {
            "lock_action": "edit",
            "lock_user": "#CONTEXT_USER_ID#"
        }},
        {"version": 1, "operation": "item_unlock"}
    ]}
    """
