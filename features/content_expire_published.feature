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
        }                    
    
    ]
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
    And we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "headline": "test", "state": "fetched", "slugline": "slugline",
      "headline": "headline",
      "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}],
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body"}]
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
    Then we get list with 2 items
    """
    {"_items" : [
      {"package_type": "takes", "_id": "#archive.123.take_package#",
       "state": "published", "type": "composite", "_current_version": 2},
      {"_id": "123", "_current_version": 1, "state": "published", "type": "text", "_current_version": 2}
      ]
    }
    """
    When we enqueue published
    When we get "/publish_queue"
    Then we get list with 2 items
    When we transmit items
    And run import legal publish queue
    And we expire items
    """
    ["123"]
    """
    And we get "/published"
    Then we get list with 2 items
    When we expire items
    """
    ["#archive.123.take_package#"]
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
       "state": "published", "type": "composite", "_current_version": 2},
      {"item_id": "123", "_current_version": 1, "state": "published", "type": "text", "_current_version": 2}
      ]
    }
    """

  @auth
  Scenario: Item in a package is published and expired
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    And we get existing resource
    """
    {"_current_version": 2, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
    """
    When we get "/published"
    Then we get list with 2 items
    """
    {"_items" : [
      {"package_type": "takes", "_id": "#archive.123.take_package#",
       "state": "published", "type": "composite", "_current_version": 2},
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
    Then we get list with 3 items
    When we enqueue published
    When we transmit items
    And run import legal publish queue
    When we get "publish_queue"
    Then we get list with 3 items
    When we expire items
    """
    ["#archive.123.take_package#"]
    """
    When we get "published"
    Then we get list with 3 items
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
    Then we get list with 2 items
    """
    {"_items" : [
      {"package_type": "takes", "_id": "#archive.123.take_package#",
       "state": "published", "type": "composite", "_current_version": 2},
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
    ["123", "#archive.123.take_package#"]
    """
    When we get "published"
    Then we get list with 5 items
    """
    {
      "_items": [
        {"_id": "123"}, {"_id": "456"}, {"_id": "#package1#"},
         {"_id": "#archive.123.take_package#"}, {"_id": "#archive.456.take_package#"}
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
    ["456", "#archive.456.take_package#"]
    """
    When we get "published"
    Then we get list with 5 items
    """
    {
      "_items": [
        {"_id": "123"}, {"_id": "456"}, {"_id": "#package1#"},
         {"_id": "#archive.123.take_package#"}, {"_id": "#archive.456.take_package#"}
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
    Then we get list with 5 items
    """
    {
      "_items": [
        {"_id": "123"}, {"_id": "456"}, {"_id": "#package1#"},
        {"_id": "#archive.123.take_package#"}, {"_id": "#archive.456.take_package#"}
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
    Then we get list with 5 items
    """
    {
      "_items": [
         {"item_id": "123"}, {"item_id": "456"}, {"item_id": "#package1#"},
         {"item_id": "#archive.123.take_package#"}, {"item_id": "#archive.456.take_package#"}
      ]
    }
    """

  @auth
  Scenario: Some of the takes are not published.
    When we post to "archive/123/link"
    """
    [{}]
    """
    Then we get next take as "take1"
    """
    {"_id": "#take1#"}
    """
    When we post to "archive/#take1#/link"
    """
    [{}]
    """
    Then we get next take as "take2"
    """
    {"_id": "#take2#"}
    """
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we expire items
    """
    ["123", "#archive.123.take_package#"]
    """
    When we get "archive"
    Then we get list with 2 items
    When we get "published"
    Then we get list with 2 items
    """
    {
      "_items": [
        {"_id": "123", "type": "text"},
        {
          "_id": "#archive.123.take_package#",
          "type": "composite",
          "sequence": 3,
          "groups": [
            {"id": "root", "refs": [{"idRef": "main"}]},
            {
              "id": "main",
              "refs": [
                {
                    "residRef": "123",
                    "location": "archive",
                    "is_published": true
                },
                {
                    "residRef": "#take1#",
                    "location": "archive"
                },
                {
                    "residRef": "#take2#",
                    "location": "archive"
                }
              ]
            }
          ]
        }
      ]
    }
    """
    When we expire items
    """
    ["#take1#", "#take2#"]
    """
    When we get "archive"
    Then we get list with 0 items
    When we get "published"
    Then we get list with 0 items
    When we get "publish_queue"
    Then we get list with 0 items
    When we get "archived"
    Then we get list with 2 items
    """
    {
      "_items": [
        {"item_id": "123", "type": "text"},
        {"item_id": "#archive.123.take_package#",
         "type": "composite",
         "sequence": 1,
         "groups": [
           {"id": "root", "refs": [{"idRef": "main"}]},
           {
             "id": "main",
             "refs": [
               {
                   "residRef": "123",
                   "location": "archived"
               }
             ]
           }
         ]
        }
      ]
    }
    """

  @auth
  Scenario: Some of the takes are not published and take is part of a package.
    When we post to "archive/123/link"
    """
    [{}]
    """
    Then we get next take as "take1"
    """
    {"_id": "#take1#"}
    """
    When we patch "archive/#take1#"
    """
    {"slugline": "testing"}
    """
    Then we get OK response
    When we post to "archive/#take1#/link"
    """
    [{}]
    """
    Then we get next take as "take2"
    """
    {"_id": "#take2#"}
    """
    When we patch "archive/#take2#"
    """
    {"slugline": "testing"}
    """
    Then we get OK response
    When we publish "123" with "publish" type and "published" state
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
                          "residRef": "#take1#"
                      }
                    ],
                    "role": "grpRole:Main"
                  }
      ]
    }
    """
    Then we get OK response
    When we expire items
    """
    ["123", "#archive.123.take_package#"]
    """
    When we get "archive"
    Then we get list with 3 items
    When we get "published"
    Then we get list with 2 items
    """
    {
      "_items": [
        {"_id": "123", "type": "text"},
        {
          "_id": "#archive.123.take_package#",
          "type": "composite",
          "sequence": 3,
          "groups": [
            {"id": "root", "refs": [{"idRef": "main"}]},
            {
              "id": "main",
              "refs": [
                {
                    "residRef": "123",
                    "location": "archive",
                    "is_published": true
                },
                {
                    "residRef": "#take1#",
                    "location": "archive"
                },
                {
                    "residRef": "#take2#",
                    "location": "archive"
                }
              ]
            }
          ]
        }
      ]
    }
    """
    When we expire items
    """
    ["#take1#", "#take2#"]
    """
    When we get "archive"
    Then we get list with 3 items
    When we get "published"
    Then we get list with 2 items
    When we get "publish_queue"
    Then we get list with 2 items
    When we expire items
    """
    ["#package1#"]
    """
    When we get "archive"
    Then we get list with 0 items
    When we get "published"
    Then we get list with 0 items
    When we get "publish_queue"
    Then we get list with 0 items
    When we get "archived"
    Then we get list with 2 items
    """
    {
      "_items": [
        {"item_id": "123", "type": "text"},
        {
          "item_id": "#archive.123.take_package#",
          "type": "composite",
          "sequence": 1,
          "groups": [
            {"id": "root", "refs": [{"idRef": "main"}]},
            {
              "id": "main",
              "refs": [
                {
                    "residRef": "123",
                    "location": "archived"
                }
              ]
            }
          ]
        }
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
    ["123", "#archive.123.take_package#"]
    """
    And we get "archive"
    Then we get list with 2 items
    When we get "published"
    Then we get list with 3 items
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
    Then we get list with 3 items
    """
    {"_items":[{"item_id": "123"}, {"item_id": "#broadcast1#"}, {"item_id": "#archive.123.take_package#"}]}
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
    ["123", "#archive.123.take_package#"]
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
    Then we get list with 3 items
    """
    {"_items":[{"item_id": "123"}, {"item_id": "#broadcast1#"}, {"item_id": "#archive.123.take_package#"}]}
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
    Then we get list with 6 items
    When we get "publish_queue"
    Then we get list with 6 items
    When we get "archived"
    Then we get list with 0 items
    When we expire items
    """
    ["123", "#archive.123.take_package#"]
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
    Then we get list with 1 items
    """
    {"_items" : [
        {"item_id": "123", "item_version": 2, "state": "success", "content_type": "text"}
      ]
    }
    """
    When we get "/legal_publish_queue?where=item_id==%22#archive.123.take_package#%22"
    Then we get list with 1 items
    """
    {"_items" : [
        {"item_id": "#archive.123.take_package#", "item_version": 2, "state": "success", "content_type": "composite"}
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
    When we get "/legal_publish_queue?where=item_id==%22#archive.456.take_package#%22"
    Then we get list with 0 items
    When we expire items
    """
    ["123", "#archive.123.take_package#", "456", "#archive.456.take_package#"]
    """
    And we get "/archive/456"
    Then we get OK response
    And we get existing resource
    """
    {"_id": "456", "type": "text", "expiry_status": "invalid"}
    """
    When we get "/archive/#archive.456.take_package#"
    Then we get OK response
    And we get existing resource
    """
    {"_id": "#archive.456.take_package#", "type": "composite", "expiry_status": "invalid"}
    """
    When we get "/archive/123"
    Then we get error 404
    When we get "/archive/#archive.123.take_package#"
    Then we get error 404
    When we expire items
    """
    ["456", "#archive.456.take_package#"]
    """
    And we get "/archive/456"
    Then we get OK response
    When we get "/archive/#archive.456.take_package#"
    Then we get OK response
    When run import legal publish queue
    And we run import legal archive command
    And we expire items
    """
    ["456", "#archive.456.take_package#"]
    """
    And we get "/archive/456"
    Then we get error 404
    When we get "/archive/#archive.456.take_package#"
    Then we get error 404
    When we get "/legal_archive/456"
    Then we get OK response
    When we get "/legal_archive/#archive.456.take_package#"
    Then we get OK response

  @auth @vocabulary @test
  Scenario: Only entertainment articles are archived
    When we publish "123" with "publish" type and "published" state
    Then we get OK response
    When we enqueue published
    And we transmit items
    And run import legal publish queue
    When we get "/legal_archive/123"
    Then we get OK response
    When we get "/legal_publish_queue?where=item_id==%22123%22"
    Then we get list with 1 items
    """
    {"_items" : [
        {"item_id": "123", "item_version": 2, "state": "success", "content_type": "text"}
      ]
    }
    """
    When we get "/legal_publish_queue?where=item_id==%22#archive.123.take_package#%22"
    Then we get list with 1 items
    """
    {"_items" : [
        {"item_id": "#archive.123.take_package#", "item_version": 2, "state": "success", "content_type": "composite"}
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
    Then we get list with 1 items
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
    Then we get list with 1 items
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
    When we expire items
    """
    ["123", "#archive.123.take_package#",
     "456", "#archive.456.take_package#",
     "789", "#archive.789.take_package#"]
    """
    And we get "/archived"
    Then we get list with 2 items
    """
    {
      "_items": [
        {"item_id": "123", "type": "text", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}]},
        {"item_id": "#archive.123.take_package#", "type": "composite",
        "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}]}
      ]
    }
    """
    When we get "/archive/456"
    Then we get error 404
    When we get "/archive/789"
    Then we get error 404
    When we get "/archive/#archive.456.take_package#"
    Then we get error 404
    When we get "/archive/#archive.789.take_package#"
    Then we get error 404
