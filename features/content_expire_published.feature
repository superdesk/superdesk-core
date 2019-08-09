Feature: Content Expiry Published Items

  Background: Setup data required to test not published items
    Given "desks"
    """
    [{"name": "Sports", "content_expiry": 60}]
    """
    And "validators"
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
        },
        {
            "schema": {},
            "type": "text",
            "act": "correct",
            "_id": "correct_text"
        },
        {
            "_id": "correct_composite",
            "act": "correct",
            "type": "composite",
            "schema": {}
        },
        {
            "schema": {},
            "type": "text",
            "act": "kill",
            "_id": "kill_text"
        },
        {
            "_id": "kill_composite",
            "act": "kill",
            "type": "composite",
            "schema": {}
        },
        {
            "_id": "publish_picture",
            "act": "publish",
            "type": "picture",
            "schema": {
                "renditions": {
                    "type": "dict",
                    "required": true,
                    "schema": {
                        "4-3": {"type": "dict", "required": true},
                        "16-9": {"type": "dict", "required": true}
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
    And we post to "highlights"
    """
    {"name": "highlight1", "desks": ["#desks._id#"]}
    """
    And we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "headline": "test", "state": "fetched", "slugline": "slugline",
      "headline": "headline",
      "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}],
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body",
      "assignment_id": "123456",
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
    Then we get OK response
    And we get existing resource
    """
    {"_current_version": 1, "state": "fetched", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
    """

  @auth
  Scenario: Item on a desk is published and expired
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    And we get existing resource
    """
    {"_current_version": 2, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
    """
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [
      {"_id": "123", "_current_version": 1, "state": "published", "type": "text", "_current_version": 2}
      ]
    }
    """
    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 2 items
    When we transmit items
    And run import legal publish queue
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 2 items
    """
    {"_items": [
      {"version": 1, "operation": "create"},
      {"version": 2, "operation": "publish"}
    ]}
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
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 0 items
    When we get "/archived"
    Then we get list with 1 items
    """
    {"_items" : [
      {"item_id": "123", "_current_version": 1, "state": "published", "type": "text", "_current_version": 2}
      ]
    }
    """

  @auth
  Scenario: Highlights and mark desks are removed from archived
    When we post to "marked_for_highlights"
    """
    [{"highlights": "#highlights._id#", "marked_item": "#archive._id#"}]
    """
    Then we get new resource
    """
    {"highlights": "#highlights._id#", "marked_item": "#archive._id#"}
    """
    When we post to "/marked_for_desks" with success
    """
    [{"marked_desk": "#desks._id#", "marked_item": "#archive._id#"}]
    """
    Then we get new resource
    """
    {"marked_desk": "#desks._id#", "marked_item": "#archive._id#"}
    """
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    And we get existing resource
    """
    {"_current_version": 2, "state": "published",
    "highlights": ["#highlights._id#"],
    "marked_desks": [{"desk_id": "#desks._id#"}],
    "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
    """
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [
      {"_id": "123", "_current_version": 1, "state": "published", "type": "text", "_current_version": 2}
      ]
    }
    """
    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 2 items
    When we transmit items
    And run import legal publish queue
    When we expire items
    """
    ["123"]
    """
    When we get "/archived"
    Then we get "highlights" does not exist
    Then we get "marked_desks" does not exist

  @auth
  Scenario: Item in a package is published and expired
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    And we get existing resource
    """
    {"_current_version": 2, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
    """
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [
      {"_id": "123", "_current_version": 1, "state": "published", "type": "text", "_current_version": 2}
      ]
    }
    """
    When we enqueue published
    When we transmit items
    And run import legal publish queue
    When we get "/publish_queue"
    Then we get list with 2 items
    When we post to "/archive" with "package" and success
    """
    {
      "guid": "package", "type": "composite", "headline": "test package", "state": "fetched",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Package",
      "groups": [
                  {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                  {
                    "id": "main",
                    "refs": [
                      {
                          "headline": "Test Document body",
                          "residRef": "123",
                          "slugline": ""
                      }
                    ],
                    "role": "grpRole:Main"
                  }
      ]
    }
    """
    When we publish "#package#" with "publish" type and "published" state
    Then we get OK response
    When we expire items
    """
    ["123"]
    """
    When we get "published"
    Then we get list with 2 items
    When we enqueue published
    When we transmit items
    And run import legal publish queue
    When we get "publish_queue"
    Then we get list with 3 items
    When we expire items
    """
    ["#package#"]
    """
    When we get "published"
    Then we get list with 0 items
    When we get "publish_queue"
    Then we get list with 0 items

  @auth
  Scenario: Item in multiple packages is published and expired
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    And we get existing resource
    """
    {"_current_version": 2, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
    """
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [
      {"_id": "123", "_current_version": 1, "state": "published", "type": "text", "_current_version": 2}
      ]
    }
    """
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    And we get "/publish_queue"
    Then we get list with 2 items
    When we post to "/archive" with success
    """
    [{"guid": "456", "type": "text", "headline": "test", "state": "fetched", "slugline": "slugline",
      "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}],
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body"}]
    """
    And we publish "456" with "publish" type and "published" state
    Then we get OK response
    When we post to "/archive" with "package1" and success
    """
    {
      "guid": "package1", "type": "composite", "headline": "test package", "state": "fetched",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Package",
      "groups": [
                  {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                  {
                    "id": "main",
                    "refs": [
                      {
                          "headline": "Test Document body",
                          "residRef": "123",
                          "slugline": ""
                      },
                      {
                          "headline": "Test Document body",
                          "residRef": "456",
                          "slugline": ""
                      }
                    ],
                    "role": "grpRole:Main"
                  }
      ]
    }
    """
    When we publish "#package1#" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we post to "/archive" with "package2" and success
    """
    {
      "guid": "package2", "type": "composite", "headline": "test package", "state": "fetched",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Package",
      "groups": [
                  {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                  {
                    "id": "main",
                    "refs": [
                      {
                          "headline": "Test Document body",
                          "residRef": "456",
                          "slugline": ""
                      }
                    ],
                    "role": "grpRole:Main"
                  }
      ]
    }
    """
    Then we get OK response
    When we transmit items
    And run import legal publish queue
    And we expire items
    """
    ["123"]
    """
    When we get "published"
    Then we get list with 3 items
    """
    {
      "_items": [
        {"_id": "123"}, {"_id": "456"}, {"_id": "#package1#"}
      ]
    }
    """
    When we enqueue published
    When we get "publish_queue"
    Then we get list with 5 items
    When we get "archive"
    Then we get list with 1 items
    """
    {
      "_items": [
        {"_id": "#package2#"}
      ]
    }
    """
    When we get "archived"
    Then we get list with 0 items
    When we expire items
    """
    ["456"]
    """
    When we get "published"
    Then we get list with 3 items
    """
    {
      "_items": [
        {"_id": "123"}, {"_id": "456"}, {"_id": "#package1#"}
      ]
    }
    """
    When we get "publish_queue"
    Then we get list with 5 items
    When we get "archive"
    Then we get list with 1 items
    """
    {
      "_items": [
        {"_id": "#package2#"}
      ]
    }
    """
    When we get "archived"
    Then we get list with 0 items
    When we expire items
    """
    ["#package1#"]
    """
    When we get "published"
    Then we get list with 3 items
    """
    {
      "_items": [
        {"_id": "123"}, {"_id": "456"}, {"_id": "#package1#"}
      ]
    }
    """
    When we get "publish_queue"
    Then we get list with 5 items
    When we get "archive"
    Then we get list with 1 items
    """
    {
      "_items": [
        {"_id": "#package2#"}
      ]
    }
    """
    When we get "archived"
    Then we get list with 0 items
    When we expire items
    """
    ["#package2#"]
    """
    When we get "published"
    Then we get list with 0 items
    When we get "publish_queue"
    Then we get list with 0 items
    When we get "archive"
    Then we get list with 0 items
    When we get "archived"
    Then we get list with 3 items
    """
    {
      "_items": [
         {"item_id": "123"}, {"item_id": "456"}, {"item_id": "#package1#"}
      ]
    }
    """


  @auth @vocabulary
  Scenario: Expire the master story then it expires all related broadcast content.
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we post to "archive/123/broadcast" with "broadcast1" and success
    """
    [{"desk": "#desks._id#"}]
    """
    Then we get OK response
    When we patch "/archive/#broadcast1#"
    """
    {"headline":"headline", "body_html": "testing", "abstract": "abstract"}
    """
    Then we get OK response
    When we post to "archive/123/broadcast" with "broadcast2" and success
    """
    [{"desk": "#desks._id#"}]
    """
    Then we get OK response
    When we patch "/archive/#broadcast2#"
    """
    {"headline":"headline", "body_html": "testing", "abstract": "abstract"}
    """
    Then we get OK response
    When we post to "archive/123/broadcast" with "broadcast3" and success
    """
    [{"desk": "#desks._id#"}]
    """
    Then we get OK response
    When we patch "/archive/#broadcast3#"
    """
    {"headline":"headline", "body_html": "testing", "abstract": "abstract"}
    """
    Then we get OK response
    When we publish "#broadcast1#" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we expire items
    """
    ["123"]
    """
    And we get "archive"
    Then we get list with 2 items
    When we get "published"
    Then we get list with 2 items
    When we get "publish_queue"
    Then we get list with 4 items
    When we get "archived"
    Then we get list with 0 items
    When we expire items
    """
    ["#broadcast1#", "#broadcast2#", "#broadcast3#"]
    """
    And we get "archive"
    Then we get list with 0 items
    When we get "published"
    Then we get list with 0 items
    When we get "publish_queue"
    Then we get list with 0 items
    When we get "archived"
    Then we get list with 2 items
    """
    {"_items":[{"item_id": "123"}, {"item_id": "#broadcast1#"}]}
    """

  @auth @vocabulary
  Scenario: Broadcast in a package then master story and broadcast content cannot expires unless package expire.
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we post to "archive/123/broadcast" with "broadcast1" and success
    """
    [{"desk": "#desks._id#"}]
    """
    Then we get OK response
    When we patch "/archive/#broadcast1#"
    """
    {"headline":"headline", "body_html": "testing", "abstract": "abstract"}
    """
    Then we get OK response
    When we post to "archive/123/broadcast" with "broadcast2" and success
    """
    [{"desk": "#desks._id#"}]
    """
    Then we get OK response
    When we patch "/archive/#broadcast2#"
    """
    {"headline":"headline", "body_html": "testing", "abstract": "abstract"}
    """
    Then we get OK response
    When we post to "archive/123/broadcast" with "broadcast3" and success
    """
    [{"desk": "#desks._id#"}]
    """
    Then we get OK response
    When we patch "/archive/#broadcast3#"
    """
    {"headline":"headline", "body_html": "testing", "abstract": "abstract"}
    """
    Then we get OK response
    When we publish "#broadcast1#" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we post to "/archive" with "package1" and success
    """
    {
      "guid": "package1", "type": "composite", "headline": "test package", "state": "fetched",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Package",
      "groups": [
                  {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                  {
                    "id": "main",
                    "refs": [
                      {
                          "headline": "Test Document body",
                          "residRef": "#broadcast2#",
                          "slugline": ""
                      }
                    ],
                    "role": "grpRole:Main"
                  }
      ]
    }
    """
    When we expire items
    """
    ["123"]
    """
    And we get "archive"
    Then we get list with 3 items
    """
    {"_items": [{"_id": "#broadcast2#"}, {"_id": "#package1#"}, {"_id": "#broadcast3#"}]}
    """
    When we get "archived"
    Then we get list with 0 items
    When we expire items
    """
    ["#package1#", "#broadcast1#", "#broadcast2#", "#broadcast3#"]
    """
    And we get "archive"
    Then we get list with 0 items
    When we get "published"
    Then we get list with 0 items
    When we get "publish_queue"
    Then we get list with 0 items
    When we get "archived"
    Then we get list with 2 items
    """
    {"_items":[{"item_id": "123"}, {"item_id": "#broadcast1#"}]}
    """

  @auth @vocabulary
  Scenario: Correct/kill an item and then expire
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we publish "123" with "correct" type and "corrected" state
    """
    {"body_html": "Corrected", "slugline": "corrected", "headline": "corrected"}
    """
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we publish "123" with "kill" type and "killed" state
    """
    {"body_html": "killed", "slugline": "killed", "headline": "killed"}
    """
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we get "archive"
    Then we get list with 0 items
    When we get "published"
    Then we get list with 3 items
    When we get "publish_queue"
    Then we get list with 6 items
    When we get "archived"
    Then we get list with 0 items
    When we expire items
    """
    ["123"]
    """
    And we get "archive"
    Then we get list with 0 items
    When we get "published"
    Then we get list with 0 items
    When we get "publish_queue"
    Then we get list with 0 items
    When we get "archived"
    Then we get list with 0 items

  @auth @vocabulary
  Scenario: Expire items that not moved to legal.
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we get "/legal_archive/123"
    Then we get OK response
    When we get "/legal_publish_queue?where=item_id==%22123%22"
    Then we get list with 2 items
    """
    {"_items" : [
        {"item_id": "123", "item_version": 2, "state": "success", "content_type": "text"}
      ]
    }
    """
    When we post to "/archive" with success
    """
    [{"guid": "456", "type": "text", "headline": "test", "state": "fetched", "slugline": "slugline",
      "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}],
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body"}]
    """
    And we publish "456" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    When we get "/legal_publish_queue?where=item_id==%22456%22"
    Then we get list with 0 items
    When we expire items
    """
    ["123", "456"]
    """
    And we get "/archive/456"
    Then we get OK response
    And we get existing resource
    """
    {"_id": "456", "type": "text", "expiry_status": "invalid"}
    """
    When we get "/archive/123"
    Then we get error 404
    When we expire items
    """
    ["456"]
    """
    And we get "/archive/456"
    Then we get OK response
    When run import legal publish queue
    And we run import legal archive command
    And we expire items
    """
    ["456"]
    """
    And we get "/archive/456"
    Then we get error 404
    When we get "/legal_archive/456"
    Then we get OK response


  @auth @vocabulary
  Scenario: Only entertainment articles are archived
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we get "/legal_archive/123"
    Then we get OK response
    When we get "/legal_publish_queue?where=item_id==%22123%22"
    Then we get list with 2 items
    """
    {"_items" : [
        {"item_id": "123", "item_version": 2, "state": "success", "content_type": "text"}
      ]
    }
    """
    When we post to "/archive" with success
    """
    [{"guid": "456", "type": "text", "headline": "test", "state": "fetched", "slugline": "slugline",
      "anpa_category" : [{"qcode" : "a", "name" : "Australian General News"}],
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body"}]
    """
    And we publish "456" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we get "/legal_archive/456"
    Then we get OK response
    When we get "/legal_publish_queue?where=item_id==%22456%22"
    Then we get list with 2 items
    When we post to "/archive" with success
    """
    [{"guid": "789", "type": "text", "headline": "test", "state": "fetched", "slugline": "slugline",
      "anpa_category" : [{"qcode" : "s", "name" : "International Sports"}],
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body"}]
    """
    And we publish "789" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we get "/legal_archive/789"
    Then we get OK response
    When we get "/legal_publish_queue?where=item_id==%22789%22"
    Then we get list with 2 items
    When we post to "/filter_conditions" with success
    """
    [{"name": "international sport", "field": "anpa_category", "operator": "in", "value": "s"}]
    """
    Then we get OK response
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}],
      "name": "intl sports", "is_archived_filter": true}]
    """
    Then we get OK response
    When we post to "/filter_conditions" with success
    """
    [{"name": "domestic", "field": "anpa_category", "operator": "in", "value": "a"}]
    """
    Then we get OK response
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}],
      "name": "Domestic News", "is_archived_filter": true}]
    """
    Then we get OK response
    When we post to "/filter_conditions" with success
    """
    [{"name": "Entertainment", "field": "anpa_category", "operator": "in", "value": "e"}]
    """
    Then we get OK response
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}],
      "name": "Entertainment"}]
    """
    Then we get OK response
    When we expire items
    """
    ["123",
     "456",
     "789"]
    """
    And we get "/archived"
    Then we get list with 1 items
    """
    {
      "_items": [
        {"item_id": "123", "type": "text", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}]}
      ]
    }
    """
    When we get "/archive/456"
    Then we get error 404
    When we get "/archive/789"
    Then we get error 404

  @auth @vocabulary
  Scenario: Published a story with associated picture and expire the items
      When upload a file "bike.jpg" to "archive" with "bike"
      And we post to "/archive/bike/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we patch "/archive/bike"
      """
      {
        "renditions": {
          "4-3": {"CropLeft":0,"CropRight":800,"CropTop":0,"CropBottom":600},
          "16-9": {"CropLeft":0,"CropRight":1280,"CropTop":0,"CropBottom":720}
        }
      }
      """
      Then we get OK response
      And we get rendition "4-3" with mimetype "image/jpeg"
      And we get rendition "16-9" with mimetype "image/jpeg"
      When we patch "/archive/123"
      """
      {
        "associations": {
          "featuremedia": {
            "_id": "bike",
            "poi": {"x": 0.2, "y": 0.3},
            "headline": "headline",
            "alt_text": "alt_text",
            "description_text": "description_text"
          }
        }
      }
      """
      Then we get OK response
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we get "/archive/123"
      Then we get OK response
      And we fetch a file "#rendition.4-3.href#"
      And we get OK response
      When we enqueue published
      And we transmit items
      And run import legal publish queue
      When we get "/legal_archive"
      Then we get list with 2 items
      When we expire items
      """
      ["123"]
      """
      And we get "/archived"
      Then we get list with 1 items
      When we expire items
      """
      ["bike"]
      """
      And we get "/archived"
      Then we get list with 2 items
      When we get "/archive"
      Then we get list with 0 items
      And we fetch a file "#rendition.4-3.href#"
      And we get OK response

  @auth @vocabulary
  Scenario: Published a story with associated picture and spike the picture
      When upload a file "bike.jpg" to "archive" with "bike"
      And we post to "/archive/bike/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we patch "/archive/bike"
      """
      {
        "renditions": {
          "4-3": {"CropLeft":0,"CropRight":800,"CropTop":0,"CropBottom":600},
          "16-9": {"CropLeft":0,"CropRight":1280,"CropTop":0,"CropBottom":720}
        }
      }
      """
      Then we get OK response
      And we get rendition "4-3" with mimetype "image/jpeg"
      And we get rendition "16-9" with mimetype "image/jpeg"
      When we patch "/archive/123"
      """
      {
        "associations": {
          "featuremedia": {
            "_id": "bike",
            "poi": {"x": 0.2, "y": 0.3},
            "headline": "headline",
            "alt_text": "alt_text",
            "description_text": "description_text"
          }
        }
      }
      """
      Then we get OK response
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we get "/archive/123"
      Then we get OK response
      And we fetch a file "#rendition.4-3.href#"
      And we get OK response
      When we enqueue published
      And we transmit items
      And run import legal publish queue
      When we spike "bike"
      Then we get error 400
      When we get "/legal_archive"
      Then we get list with 2 items
      When we expire items
      """
      ["bike"]
      """
      And we get "/archived"
      Then we get list with 0 items
      When we expire items
      """
      ["123", "bike"]
      """
      And we get "/archived"
      Then we get list with 2 items
      When we get "/archive"
      Then we get list with 0 items
      And we fetch a file "#rendition.4-3.href#"
      And we get OK response

  @auth @vocabulary
  Scenario: Published a story with associated picture and expire the items
      When upload a file "bike.jpg" to "archive" with "bike"
      And we post to "/archive/bike/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we patch "/archive/bike"
      """
      {
        "renditions": {
          "4-3": {"CropLeft":0,"CropRight":800,"CropTop":0,"CropBottom":600},
          "16-9": {"CropLeft":0,"CropRight":1280,"CropTop":0,"CropBottom":720}
        }
      }
      """
      Then we get OK response
      And we get rendition "4-3" with mimetype "image/jpeg"
      And we get rendition "16-9" with mimetype "image/jpeg"
      When we patch "/archive/123"
      """
      {
        "associations": {
          "featuremedia": {
            "_id": "bike",
            "poi": {"x": 0.2, "y": 0.3},
            "headline": "headline",
            "alt_text": "alt_text",
            "description_text": "description_text"
          }
        }
      }
      """
      Then we get OK response
      When we publish "123" with "publish" type and "published" state
      Then we get OK response
      When we get "/archive/123"
      Then we get OK response
      And we fetch a file "#rendition.4-3.href#"
      And we get OK response
      When we enqueue published
      And we transmit items
      And run import legal publish queue
      When we get "/legal_archive"
      Then we get list with 2 items
      When we expire items
      """
      ["123"]
      """
      And we get "/archived"
      Then we get list with 1 items
      When we expire items
      """
      ["bike"]
      """
      And we get "/archived"
      Then we get list with 2 items
      When we get "/archive"
      Then we get list with 0 items
      And we fetch a file "#rendition.4-3.href#"
      And we get OK response

  @auth @vocabulary
  Scenario: Published a story with associated picture and expire the items with PUBLISH_ASSOCIATED_ITEMS as false
      Given config update
      """
      { "PUBLISH_ASSOCIATED_ITEMS": false}
      """
      When upload a file "bike.jpg" to "archive" with "bike"
      And we post to "/archive/bike/move"
      """
      [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
      """
      Then we get OK response
      When we patch "/archive/bike"
      """
      {
        "renditions": {
          "4-3": {"CropLeft":0,"CropRight":800,"CropTop":0,"CropBottom":600},
          "16-9": {"CropLeft":0,"CropRight":1280,"CropTop":0,"CropBottom":720}
        }
      }
      """
      Then we get OK response
      And we get rendition "4-3" with mimetype "image/jpeg"
      And we get rendition "16-9" with mimetype "image/jpeg"
      When we patch "/archive/123"
      """
      {
        "associations": {
          "featuremedia": {
            "_id": "bike",
            "poi": {"x": 0.2, "y": 0.3},
            "headline": "headline",
            "alt_text": "alt_text",
            "description_text": "description_text"
          }
        }
      }
      """
      Then we get OK response
      When we publish "123" with "publish" type and "published" state
      Then we get OK response

      When we get "/published"
      Then we get list with 1 items
      """
      {"_items" : [
        {"guid": "123", "_current_version": 3, "state": "published", "type": "text", "operation": "publish",
        "associations": {"featuremedia": {"operation": "publish", "state": "published"}}}
        ]
      }
      """
      When we get "/archive/123"
      Then we get existing resource
      """
        {"guid": "123", "_current_version": 3, "state": "published", "type": "text", "operation": "publish",
        "associations": {"featuremedia": {"operation": "update", "state": "in_progress"}}
      }
      """
      Then we get OK response
      And we fetch a file "#rendition.4-3.href#"
      And we get OK response
      When we enqueue published
      And we transmit items
      And run import legal publish queue
      When we get "/legal_archive"
      Then we get list with 1 items
      When we expire items
      """
      ["123"]
      """
      And we get "/archived"
      Then we get list with 1 items
      When we expire items
      """
      ["bike"]
      """
      And we get "/archived"
      Then we get list with 1 items
      When we get "/archive"
      Then we get list with 0 items
      And we fetch a file "#rendition.4-3.href#"
      And we get OK response

  @auth @vocabulary
  Scenario: Correct/takedown an item and then expire
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we publish "123" with "correct" type and "corrected" state
    """
    {"body_html": "Corrected", "slugline": "corrected", "headline": "corrected"}
    """
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we publish "123" with "takedown" type and "recalled" state
    """
    {"body_html": "recalled", "slugline": "recalled", "headline": "recalled"}
    """
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we get "archive"
    Then we get list with 0 items
    When we get "published"
    Then we get list with 3 items
    When we get "publish_queue"
    Then we get list with 6 items
    When we get "archived"
    Then we get list with 0 items
    When we expire items
    """
    ["123"]
    """
    And we get "archive"
    Then we get list with 0 items
    When we get "published"
    Then we get list with 0 items
    When we get "publish_queue"
    Then we get list with 0 items
    When we get "archived"
    Then we get list with 0 items

  @auth
  Scenario: Published content is not expired if the desk has preserve_published_content as True
    When we patch "/desks/#desks._id#"
    """
    {"preserve_published_content": true}
    """
    Then we get existing resource
    """
    {"_id": "#desks._id#", "preserve_published_content": true, "name": "Sports"}
    """
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    And we get existing resource
    """
    {"_current_version": 2, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
    """
    When we get "/published"
    Then we get list with 1 items
    """
    {
      "_items" : [
        {"_id": "123", "state": "published", "type": "text", "_current_version": 2}
      ]
    }
    """
    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 2 items
    When we transmit items
    And run import legal publish queue
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 2 items
    """
    {"_items": [
      {"version": 1, "operation": "create"},
      {"version": 2, "operation": "publish"}
    ]}
    """
    When we expire items
    """
    ["123"]
    """
    And we get "/published"
    Then we get list with 1 items
    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 2 items
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 2 items
    When we get "/archived"
    Then we get list with 0 items


  @auth @vocabulary
  Scenario: Correct/takedown an item and then expire on desk with preserve_published_content as True
    When we patch "/desks/#desks._id#"
    """
    {"preserve_published_content": true}
    """
    Then we get existing resource
    """
    {"_id": "#desks._id#", "preserve_published_content": true, "name": "Sports"}
    """
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we expire items
    """
    ["123"]
    """
    And we get "/published"
    Then we get list with 1 items
    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 2 items
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 2 items
    When we get "/archived"
    Then we get list with 0 items
    When we publish "123" with "correct" type and "corrected" state
    """
    {"body_html": "Corrected", "slugline": "corrected", "headline": "corrected"}
    """
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we expire items
    """
    ["123"]
    """
    And we get "/published"
    Then we get list with 2 items
    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 4 items
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 3 items
    When we get "/archived"
    Then we get list with 0 items
    When we publish "123" with "takedown" type and "recalled" state
    """
    {"body_html": "recalled", "slugline": "recalled", "headline": "recalled"}
    """
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we get "archive"
    Then we get list with 0 items
    When we get "published"
    Then we get list with 3 items
    When we get "publish_queue"
    Then we get list with 6 items
    When we get "archived"
    Then we get list with 0 items
    When we expire items
    """
    ["123"]
    """
    And we get "archive"
    Then we get list with 0 items
    When we get "published"
    Then we get list with 0 items
    When we get "publish_queue"
    Then we get list with 0 items
    When we get "archived"
    Then we get list with 0 items

  @auth
  Scenario: Published content is expired if the preserve_published_content flag is changed to false
    When we patch "/desks/#desks._id#"
    """
    {"preserve_published_content": true}
    """
    Then we get existing resource
    """
    {"_id": "#desks._id#", "preserve_published_content": true, "name": "Sports"}
    """
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    And we get existing resource
    """
    {"_current_version": 2, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
    """
    When we get "/published"
    Then we get list with 1 items
    """
    {
      "_items" : [
        {"_id": "123", "state": "published", "type": "text", "_current_version": 2}
      ]
    }
    """
    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 2 items
    When we transmit items
    And run import legal publish queue
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 2 items
    """
    {"_items": [
      {"version": 1, "operation": "create"},
      {"version": 2, "operation": "publish"}
    ]}
    """
    When we expire items
    """
    ["123"]
    """
    And we get "/published"
    Then we get list with 1 items
    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 2 items
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 2 items
    When we get "/archived"
    Then we get list with 0 items
    When we patch "/desks/#desks._id#"
    """
    {"preserve_published_content": false}
    """
    Then we get existing resource
    """
    {"_id": "#desks._id#", "preserve_published_content": false, "name": "Sports"}
    """
    When we expire items
    """
    ["123"]
    """
    When we get "/published"
    Then we get list with 0 items
    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 0 items
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 0 items
    When we get "/archived"
    Then we get list with 1 items
