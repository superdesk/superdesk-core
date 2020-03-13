Feature: Kill a content item in the (dusty) archive

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
    When we post to "/products" with success
    """
    {
      "name":"prod-1","codes":"abc,xyz", "product_type": "both"
    }
    """
    Given "subscribers"
    """
    [{
      "name":"Channel 1", "media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["#products._id#"], "_id": "s-d",
      "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
    },
    {
      "name":"Channel 2", "media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["#products._id#"], "_id": "s-w",
      "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
    }]
    """
    When we post to "content_templates"
    """
    {"template_name": "kill", "template_type": "kill",
     "data": {"body_html": "<p>Story killed due to court case. Please remove the story from your archive.<\/p>",
              "type": "text", "abstract": "This article has been removed", "headline": "Kill\/Takedown notice ~~~ Kill\/Takedown notice",
              "urgency": 1, "priority": 1,  "anpa_take_key": "KILL\/TAKEDOWN"}
    }
    """

  @auth @notification
  Scenario: Kill a Text Article in the Dusty Archive
    When we post to "/subscribers" with "api" and success
    """
    {
      "name":"Channel api", "media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "api_products": ["#products._id#"]
    }
    """
    And we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "state": "fetched", "slugline": "archived",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}],
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "target_types": [{"qcode": "digital", "allow": false}],
      "dateline" : {
        "located" : {
            "state_code" : "NSW",
            "city" : "Sydney",
            "tz" : "Australia/Sydney",
            "country_code" : "AU",
            "dateline" : "city",
            "alt_name" : "",
            "state" : "New South Wales",
            "city_code" : "Sydney",
            "country" : "Australia"
        },
        "source" : "AAP",
        "date" : "2016-04-13T04:29:14",
        "text" : "SYDNEY April 13 AAP -"
      },
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
    When run import legal publish queue
    And we get "/legal_publish_queue"
    Then we get list with 1 items
    """
    {"_items" : [
        {"item_id": "123", "subscriber_id":"Channel api", "content_type": "text",
        "item_version": 2, "publishing_action": "published"}
     ]}
    """
    When we transmit items
    And run import legal publish queue
    When we get "/legal_publish_queue"
    Then we get list with 2 items
    """
    {"_items" : [
        {"item_id": "123", "subscriber_id":"Channel api", "content_type": "text",
        "item_version": 2, "publishing_action": "published"},
        {"item_id": "123", "subscriber_id":"Channel 2", "content_type": "text",
        "item_version": 2, "publishing_action": "published"}
     ]}
    """
    When we expire items
    """
    ["123"]
    """
    And we get "/published"
    Then we get list with 0 items
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 0 items
    When we get "/archived"
    Then we get list with 1 items
    """
    {"_items" : [{"item_id": "123", "state": "published", "type": "text", "_current_version": 2}]}
    """
    When we get "/legal_publish_queue"
    Then we get list with 2 items
    When we patch "/archived/123:2"
    """
    {"body_html": "Killed body.", "operation": "kill"}
    """
    Then we get OK response
    And we get 1 emails
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [{"_id": "123", "state": "killed", "type": "text", "_current_version": 3, "queue_state": "queued"}]}
    """
    When we transmit items
    And run import legal publish queue
    And we get "/legal_publish_queue"
    Then we get list with 4 items
    """
    {"_items" : [
        {"item_id": "123", "subscriber_id":"Channel api", "content_type": "text",
        "item_version": 2, "publishing_action": "published"},
        {"item_id": "123", "subscriber_id":"Channel 2", "content_type": "text",
        "item_version": 2, "publishing_action": "published"},
        {"item_id": "123", "subscriber_id":"Channel api", "content_type": "text",
        "item_version": 3, "publishing_action": "killed"},
        {"item_id": "123", "subscriber_id":"Channel 2", "content_type": "text",
        "item_version": 3, "publishing_action": "killed"}
     ]}
    """
    When we get "/archive/123"
    Then we get OK response
    And we get text "Please kill story slugged archived" in response field "body_html"
    And we get text "Killed body" in response field "body_html"
    And we get emails
    """
    [
      {"body": "Please kill story slugged archived"},
      {"body": "Killed body"}
    ]
    """
    When we get "/archived/123:2"
    Then we get error 404
    When we get "/archived"
    Then we get list with 0 items
    When we get "/legal_archive/123"
    Then we get existing resource
    """
    {"_id": "123", "type": "text", "_current_version": 3, "state": "killed", "pubstatus": "canceled", "operation": "kill"}
    """
    When we get "/legal_archive/123?version=all"
    Then we get list with 3 items
    When we expire items
    """
    ["123"]
    """
    And we get "/published"
    Then we get list with 0 items
    When we get "/archive"
    Then we get list with 0 items

  @auth @notification
  Scenario: Kill a Text Article that exists only in Archived
    Given "archived" with objectid
    """
    [{
      "_id": "56aad5a61d41c8aa98ddd015", "guid": "123", "item_id": "123", "_current_version": "1", "type": "text", "abstract": "test", "state": "fetched", "slugline": "slugline",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}],
      "flags" : {"marked_archived_only": true},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body"
    }]
    """
    When we patch "/archived/56aad5a61d41c8aa98ddd015"
    """
    {"operation": "kill"}
    """
    When we get "/archived"
    Then we get list with 0 items
    And we get 1 emails

  @auth @notification
  Scenario: Kill a Text Article also kills the Digital Story in the Dusty Archive
    Given "archived"
    """
    [{"item_id": "123", "guid": "123", "type": "text", "abstract": "test", "slugline": "slugline",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "linked_in_packages": [{"package" : "234", "package_type" : "takes"}], "is_take_item" : true,
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2},
     {"groups": [{"id": "root", "refs": [{"idRef": "main"}]},
                {"id": "main", "refs": [{"headline": "headline", "slugline": "slugline", "residRef": "123"}]}
               ],
      "item_id": "234", "guid": "234", "type": "composite", "_current_version": 2, "state": "published",
      "package_type" : "takes", "is_take_item" : false,
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
    ]
    """
    And "legal_archive"
    """
    [{"_id" : "123", "type" : "text", "guid" : "123", "_current_version" : 2,
      "linked_in_packages" : [{"package_type" : "takes", "package" : "234"}],
      "operation" : "publish", "state": "published", "pubstatus" : "usable"},
      {"_id" : "234", "type" : "composite", "guid" : "123", "_current_version" : 2,
      "groups" : [
        {"id" : "root", "role" : "grpRole:NEP", "refs" : [{"idRef" : "main"}]},
        {"id" : "main", "role" : "grpRole:main", "refs" : [{"renditions" : {}, "guid" : "123", "is_published" : true,
        "location" : "legal_archive", "itemClass" : "icls:text", "_current_version" : 2, "slugline" : "slugline",
        "headline" : "headline", "residRef" : "123", "type" : "text", "sequence" : 1}]}],
      "operation" : "publish", "state": "published", "pubstatus" : "usable"}
    ]
    """
    And "legal_publish_queue"
    """
    [
        {"item_id": "123", "subscriber_id":"Channel 2", "content_type": "text",
        "item_version": 2, "publishing_action": "published", "_subscriber_id": "s-w"},
        {"item_id": "234", "subscriber_id":"Channel 1", "content_type": "text",
        "item_version": 2, "publishing_action": "published", "_subscriber_id": "s-d"}
     ]
    """
    And "legal_archive_versions" with objectid
    """
    [
        {"_id": "56aad5a61d41c8aa98ddd015", "_id_document" : "234", "guid" : "234", "_current_version" : 2},
        {"_id": "56aad5a61d41c8aa98ddd017", "_id_document" : "123", "guid" : "123", "_current_version" : 1},
        {"_id": "56aad5a61d41c8aa98ddd019", "_id_document" : "123", "guid" : "123", "_current_version" : 2}
     ]
    """
    When we patch "/archived/123:2"
    """
    {"body_html": "Killed body", "operation": "kill"}
    """
    Then we get OK response
    And we get 2 emails
    When we get "/published"
    Then we get list with 2 items
    When we get "/publish_queue"
    Then we get list with 2 items
    When we get "/archive/123"
    Then we get OK response
    And we get text "Please kill story slugged slugline" in response field "body_html"
    And we get text "Killed body" in response field "body_html"
    When we get "/archived"
    Then we get list with 0 items
    When we transmit items
    And run import legal publish queue
    When we get "/legal_archive/123"
    Then we get existing resource
    """
    {"_id": "123", "type": "text", "_current_version": 3, "state": "killed", "pubstatus": "canceled", "operation": "kill"}
    """
    When we get "/legal_archive/123?version=all"
    Then we get list with 3 items
    When we get "/legal_publish_queue"
    Then we get list with 4 items
    When we expire items
    """
    ["123", "234"]
    """
    And we get "/published"
    Then we get list with 0 items

  @auth @notification
  Scenario: Killing Take in Dusty Archive will kill other takes including the Digital Story
    Given "archived"
    """
    [
      {
        "_current_version" : 3,
        "item_id" : "234",
        "state" : "published",
        "groups" : [
            {
                "id" : "root",
                "role" : "grpRole:NEP",
                "refs" : [
                    {
                        "idRef" : "main"
                    }
                ]
            },
            {
                "id" : "main",
                "role" : "grpRole:main",
                "refs" : [
                    {
                        "headline" : "headline",
                        "renditions" : {},
                        "residRef" : "123",
                        "slugline" : "slugline",
                        "type" : "text",
                        "is_published" : true,
                        "location" : "archived",
                        "sequence" : 1,
                        "_current_version" : 2,
                        "guid" : "123",
                        "itemClass" : "icls:text"
                    }
                ]
            }
        ],
        "guid" : "234",
        "headline" : "headline",
        "publish_sequence_no" : 1,
        "sequence" : 1,
        "type" : "composite",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "digital_item_id" : "234"
    },{
        "item_id" : "123",
        "state" : "published",
        "guid" : "123",
        "headline" : "headline",
        "linked_in_packages" : [
            {
                "package" : "234",
                "package_type" : "takes"
            }
        ],
        "publish_sequence_no" : 2,
        "sequence" : 1,
        "type" : "text",
        "digital_item_id" : "234",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "_current_version" : 2
    },{
        "_current_version" : 4,
        "item_id" : "234",
        "state" : "corrected",
        "groups" : [
            {
                "id" : "root",
                "role" : "grpRole:NEP",
                "refs" : [
                    {
                        "idRef" : "main"
                    }
                ]
            },
            {
                "id" : "main",
                "role" : "grpRole:main",
                "refs" : [
                    {
                        "headline" : "corrected",
                        "renditions" : {},
                        "residRef" : "123",
                        "slugline" : "corrected",
                        "type" : "text",
                        "location" : "archived",
                        "sequence" : 1,
                        "_current_version" : 3,
                        "itemClass" : "icls:text",
                        "guid" : "123",
                        "is_published" : true
                    }
                ]
            }
        ],
        "guid" : "234",
        "headline" : "corrected",
        "publish_sequence_no" : 3,
        "sequence" : 1,
        "type" : "composite",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "digital_item_id" : "234"
    },{
        "item_id" : "123",
        "state" : "corrected",
        "guid" : "123",
        "headline" : "corrected",
        "linked_in_packages" : [
            {
                "package" : "234",
                "package_type" : "takes"
            }
        ],
        "publish_sequence_no" : 4,
        "sequence" : 1,
        "type" : "text",
        "digital_item_id" : "234",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "_current_version" : 3
    },{
        "_current_version" : 5,
        "item_id" : "234",
        "state" : "corrected",
        "groups" : [
            {
                "id" : "root",
                "role" : "grpRole:NEP",
                "refs" : [
                    {
                        "idRef" : "main"
                    }
                ]
            },
            {
                "id" : "main",
                "role" : "grpRole:main",
                "refs" : [
                    {
                        "headline" : "corrected",
                        "renditions" : {},
                        "residRef" : "123",
                        "slugline" : "corrected",
                        "type" : "text",
                        "is_published" : true,
                        "location" : "archived",
                        "sequence" : 1,
                        "_current_version" : 3,
                        "guid" : "123",
                        "itemClass" : "icls:text"
                    },
                    {
                        "headline" : "Take 1",
                        "renditions" : {},
                        "residRef" : "456",
                        "slugline" : "slugline",
                        "type" : "text",
                        "is_published" : true,
                        "location" : "archived",
                        "sequence" : 2,
                        "_current_version" : 3,
                        "guid" : "456",
                        "itemClass" : "icls:text"
                    }
                ]
            }
        ],
        "guid" : "234",
        "headline" : "Take 1",
        "publish_sequence_no" : 5,
        "sequence" : 2,
        "type" : "composite",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "digital_item_id" : "234"
    },{
        "_current_version" : 3,
        "item_id" : "456",
        "state" : "published",
        "guid" : "456",
        "headline" : "Take 1",
        "linked_in_packages" : [
            {
                "package" : "234",
                "package_type" : "takes"
            }
        ],
        "publish_sequence_no" : 6,
        "sequence" : 2,
        "type" : "text",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "digital_item_id" : "234"
    },{
        "_current_version" : 6,
        "item_id" : "234",
        "state" : "corrected",
        "groups" : [
            {
                "id" : "root",
                "role" : "grpRole:NEP",
                "refs" : [
                    {
                        "idRef" : "main"
                    }
                ]
            },
            {
                "id" : "main",
                "role" : "grpRole:main",
                "refs" : [
                    {
                        "headline" : "corrected",
                        "renditions" : {},
                        "residRef" : "123",
                        "slugline" : "corrected",
                        "type" : "text",
                        "location" : "archived",
                        "sequence" : 1,
                        "_current_version" : 3,
                        "itemClass" : "icls:text",
                        "guid" : "123",
                        "is_published" : true
                    },
                    {
                        "headline" : "Take 1",
                        "renditions" : {},
                        "residRef" : "456",
                        "slugline" : "slugline",
                        "type" : "text",
                        "location" : "archived",
                        "sequence" : 2,
                        "_current_version" : 3,
                        "itemClass" : "icls:text",
                        "guid" : "456",
                        "is_published" : true
                    },
                    {
                        "headline" : "Take 2",
                        "renditions" : {},
                        "residRef" : "789",
                        "slugline" : "slugline",
                        "type" : "text",
                        "is_published" : true,
                        "location" : "archived",
                        "sequence" : 3,
                        "_current_version" : 3,
                        "guid" : "789",
                        "itemClass" : "icls:text"
                    }
                ]
            }
        ],
        "guid" : "234",
        "headline" : "Take 2",
        "publish_sequence_no" : 7,
        "sequence" : 3,
        "type" : "composite",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "digital_item_id" : "234"
    },{
        "_current_version" : 3,
        "item_id" : "789",
        "state" : "published",
        "guid" : "789",
        "headline" : "Take 2",
        "linked_in_packages" : [
            {
                "package" : "234",
                "package_type" : "takes"
            }
        ],
        "publish_sequence_no" : 8,
        "sequence" : 3,
        "type" : "text",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "digital_item_id" : "234"
    }
    ]
    """
    And "legal_archive"
    """
    [
      {
        "_id" : "234",
        "headline" : "Take 2",
        "operation" : "publish",
        "_current_version" : 6,
        "sequence" : 3,
        "type" : "composite",
        "groups" : [
            {
                "id" : "root",
                "role" : "grpRole:NEP",
                "refs" : [
                    {
                        "idRef" : "main"
                    }
                ]
            },
            {
                "id" : "main",
                "role" : "grpRole:main",
                "refs" : [
                    {
                        "headline" : "corrected",
                        "renditions" : {},
                        "residRef" : "123",
                        "slugline" : "corrected",
                        "type" : "text",
                        "location" : "legal_archive",
                        "sequence" : 1,
                        "_current_version" : 3,
                        "itemClass" : "icls:text",
                        "guid" : "123",
                        "is_published" : true
                    },
                    {
                        "headline" : "Take 1",
                        "renditions" : {},
                        "residRef" : "456",
                        "slugline" : "slugline",
                        "type" : "text",
                        "location" : "legal_archive",
                        "sequence" : 2,
                        "_current_version" : 3,
                        "itemClass" : "icls:text",
                        "guid" : "456",
                        "is_published" : true
                    },
                    {
                        "headline" : "Take 2",
                        "renditions" : {},
                        "residRef" : "789",
                        "slugline" : "slugline",
                        "type" : "text",
                        "is_published" : true,
                        "location" : "legal_archive",
                        "sequence" : 3,
                        "_current_version" : 3,
                        "guid" : "789",
                        "itemClass" : "icls:text"
                    }
                ]
            }
        ],
        "guid" : "234",
        "state" : "corrected",
        "pubstatus" : "usable"
    },{
        "_id" : "123",
        "headline" : "corrected",
        "linked_in_packages" : [
            {
                "package" : "234",
                "package_type" : "takes"
            }
        ],
        "operation" : "correct",
        "_current_version" : 3,
        "state" : "corrected",
        "sequence" : 1,
        "type" : "text",
        "pubstatus" : "usable",
        "guid" : "123"
    },{
        "_id" : "456",
        "headline" : "Take 1",
        "linked_in_packages" : [
            {
                "package" : "234",
                "package_type" : "takes"
            }
        ],
        "operation" : "publish",
        "_current_version" : 3,
        "sequence" : 2,
        "type" : "text",
        "guid" : "456",
        "state" : "published",
        "pubstatus" : "usable"
    },{
        "_id" : "789",
        "headline" : "Take 2",
        "linked_in_packages" : [
            {
                "package" : "234",
                "package_type" : "takes"
            }
        ],
        "operation" : "publish",
        "_current_version" : 3,
        "sequence" : 3,
        "type" : "text",
        "guid" : "789",
        "state" : "published",
        "pubstatus" : "usable"
    }
    ]
    """
    And "legal_publish_queue"
    """
    [
      {
          "subscriber_id" : "Channel 1",
          "_subscriber_id" : "s-d",
          "content_type" : "composite",
          "publishing_action" : "published",
          "item_id" : "234",
          "item_version" : 3
      },{
          "subscriber_id" : "Channel 2",
          "_subscriber_id" : "s-w",
          "content_type" : "text",
          "publishing_action" : "published",
          "item_id" : "123",
          "item_version" : 2
      },{
          "subscriber_id" : "Channel 1",
          "_subscriber_id" : "s-d",
          "content_type" : "composite",
          "publishing_action" : "corrected",
          "item_id" : "234",
          "item_version" : 4
      },{
          "subscriber_id" : "Channel 2",
          "_subscriber_id" : "s-w",
          "content_type" : "text",
          "publishing_action" : "corrected",
          "item_id" : "123",
          "item_version" : 3
      },{
          "subscriber_id" : "Channel 1",
          "_subscriber_id" : "s-d",
          "content_type" : "composite",
          "publishing_action" : "published",
          "item_id" : "234",
          "item_version" : 5
      },{
          "subscriber_id" : "Channel 2",
          "_subscriber_id" : "s-w",
          "content_type" : "text",
          "publishing_action" : "published",
          "item_id" : "456",
          "item_version" : 3
      },{
          "subscriber_id" : "Channel 1",
          "_subscriber_id" : "s-d",
          "content_type" : "composite",
          "publishing_action" : "published",
          "item_id" : "234",
          "item_version" : 6
      },{
          "subscriber_id" : "Channel 2",
          "_subscriber_id" : "s-w",
          "content_type" : "text",
          "publishing_action" : "published",
          "item_id" : "789",
          "item_version" : 3
      }
    ]
    """
    And "legal_archive_versions" with objectid
    """
    [
        {
            "_id" : "59447e781d41c8818c61f3dc",
            "_current_version" : 3,
            "_id_document" : "234",
            "guid" : "234"
        },{
            "_id" : "59447e771d41c8818c61f3c6",
            "_current_version" : 1,
            "_id_document" : "234",
            "guid" : "234"
        },{
            "_id" : "59447e771d41c8818c61f3d3",
            "_current_version" : 2,
            "_id_document" : "234",
            "guid" : "234"
        },{
            "_id" : "59447e781d41c8818c61f3e4",
            "_current_version" : 2,
            "_id_document" : "123",
            "guid" : "123"
        },{
            "_id" : "59447e771d41c8818c61f3bd",
            "_current_version" : 1,
            "_id_document" : "123",
            "guid" : "123"
        },{
            "_id" : "59447e781d41c8818c61f3e7",
            "_current_version" : 4,
            "_id_document" : "234",
            "guid" : "234"
        },{
            "_id" : "59447e791d41c8818c61f3ef",
            "_current_version" : 3,
            "_id_document" : "123",
            "guid" : "123"
        },{
            "_id" : "59447e791d41c8818c61f3f2",
            "_current_version" : 5,
            "_id_document" : "234",
            "guid" : "234"
        },{
            "_id" : "59447e791d41c8818c61f3fa",
            "_current_version" : 3,
            "_id_document" : "456",
            "guid" : "456"
        },{
            "_id" : "59447e771d41c8818c61f3c8",
            "_current_version" : 1,
            "_id_document" : "456",
            "guid" : "456"
        },{
            "_id" : "59447e771d41c8818c61f3ca",
            "_current_version" : 2,
            "_id_document" : "456",
            "guid" : "456"
        },{
            "_id" : "59447e791d41c8818c61f3fd",
            "_current_version" : 6,
            "_id_document" : "234",
            "guid" : "234"
        },{
            "_id" : "59447e791d41c8818c61f405",
            "_current_version" : 3,
            "_id_document" : "789",
            "guid" : "789"
        },{
            "_id" : "59447e781d41c8818c61f3d7",
            "_current_version" : 2,
            "_id_document" : "789",
            "guid" : "789"
        },{
            "_id" : "59447e771d41c8818c61f3d5",
            "_current_version" : 1,
            "_id_document" : "789",
            "guid" : "789"
        }
     ]
    """
    When we patch "/archived/123:2"
    """
    {"operation": "kill"}
    """
    Then we get OK response
    And we get 4 emails
    When we get "/published"
    Then we get list with 4 items
    When we get "/publish_queue"
    Then we get list with 4 items
    When we get "/archived"
    Then we get list with 0 items
    When we transmit items
    And run import legal publish queue
    When we get "/legal_archive/123"
    Then we get existing resource
    """
    {"_id": "123", "type": "text", "_current_version": 4, "state": "killed", "pubstatus": "canceled", "operation": "kill"}
    """
    When we get "/legal_archive/123?version=all"
    Then we get list with 4 items
    When we get "/legal_archive/234"
    Then we get existing resource
    """
    {"_id": "234", "type": "composite", "_current_version": 7, "state": "killed", "pubstatus": "canceled", "operation": "kill"}
    """
    When we get "/legal_archive/234?version=all"
    Then we get list with 7 items
    When we get "/legal_archive/456"
    Then we get existing resource
    """
    {"_id": "456", "type": "text", "_current_version": 4, "state": "killed", "pubstatus": "canceled", "operation": "kill"}
    """
    When we get "/legal_archive/456?version=all"
    Then we get list with 4 items
    When we get "/legal_archive/789"
    Then we get existing resource
    """
    {"_id": "789", "type": "text", "_current_version": 4, "state": "killed", "pubstatus": "canceled", "operation": "kill"}
    """
    When we get "/legal_archive/789?version=all"
    Then we get list with 4 items
    When we expire items
    """
    ["123", "456", "789", "234"]
    """
    And we get "/published"
    Then we get list with 0 items


  @auth
  Scenario: Killing an article other than Text isn't allowed
    Given "archived"
    """
    [{"item_id": "123", "guid": "123", "type": "preformatted", "headline": "test", "slugline": "slugline",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2}]
    """
    When we delete "/archived/#archived._id#"
    Then we get error 400
    """
    {"_message": "Only Text articles are allowed to be Killed in Archived repo"}
    """

  @auth
  Scenario: Killing a Broadcast isn't allowed
    Given "archived"
    """
    [{"item_id": "123", "guid": "123", "type": "text", "headline": "test", "slugline": "slugline",
      "genre": [{"name": "Broadcast Script", "qcode": "Broadcast Script"}], "headline": "headline",
      "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2}]
    """
    When we delete "/archived/#archived._id#"
    Then we get error 400
    """
    {"_message": "Killing of Broadcast Items isn't allowed in Archived repo"}
    """

  @auth
  Scenario: Killing an article isn't allowed if it's available in production
    Given "archive"
    """
    [{"guid": "123", "type": "text", "headline": "test", "slugline": "slugline",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2}]
    """
    And "archived"
    """
    [{"item_id": "123", "guid": "123", "type": "text", "headline": "test", "slugline": "slugline",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2}]
    """
    When we delete "/archived/#archived._id#"
    Then we get error 400
    """
    {"_message": "Can't Kill as article is still available in production"}
    """

  @auth
  Scenario: Killing an article isn't allowed if it's part of a package
    Given "archived"
    """
    [{"item_id": "123", "guid": "123", "type": "text", "headline": "test", "slugline": "slugline",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "linked_in_packages": [{"package" : "234"}],
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2},
     {"groups": [{"id": "root", "refs": [{"idRef": "main"}]},
                {"id": "main", "refs": [{"headline": "headline", "slugline": "slugline", "residRef": "123"}]}
               ],
      "item_id": "234", "guid": "234", "type": "composite", "_current_version": 2, "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
    ]
    """
    When we delete "/archived/123:2"
    Then we get error 400
    """
    {"_message": "Can't kill as article is part of a Package"}
    """

  @auth
  Scenario: Killing an article isn't allowed if it's associated digital story is part of a package
    Given "archived"
    """
    [
     {"item_id": "123", "guid": "123", "type": "text", "headline": "test", "slugline": "slugline",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "linked_in_packages": [{"package_type" : "takes", "package" : "234"}],
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2},
     {"groups": [{"id": "root", "refs": [{"idRef": "main"}]},
                {"id": "main", "refs": [{"headline": "headline", "slugline": "slugline", "residRef": "123", "sequence": 1}]}
               ],
      "linked_in_packages": [{"package" : "345"}],
      "item_id": "234", "guid": "234", "type": "composite", "package_type": "takes", "sequence": 1, "_current_version": 2,
      "state": "published", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}},
     {"groups": [{"id": "root", "refs": [{"idRef": "main"}]},
                {"id": "main", "refs": [{"headline": "headline", "slugline": "slugline", "residRef": "234"}]}
               ],
      "item_id": "345", "guid": "345", "type": "composite", "_current_version": 2, "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
    ]
    """
    When we delete "/archived/123:2"
    Then we get error 400
    """
    {"_message": "Can't kill as article is part of a Package"}
    """

  @auth
  Scenario: Killing an article isn't allowed if any of the takes are available in production
    Given "archive"
    """
    [
     {"item_id": "234", "guid": "234", "type": "text", "headline": "Take-2", "slugline": "Take-2",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "linked_in_packages": [{"package_type" : "takes", "package" : "345"}],
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2}
    ]
    """
    And "archived"
    """
    [
     {"item_id": "123", "guid": "123", "type": "text", "headline": "Take-1", "slugline": "Take-1",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "linked_in_packages": [{"package_type" : "takes", "package" : "345"}],
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2},
     {"item_id": "234", "guid": "234", "type": "text", "headline": "Take-2", "slugline": "Take-2",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "linked_in_packages": [{"package_type" : "takes", "package" : "345"}],
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2},
     {"groups": [{"id": "root", "refs": [{"idRef": "main"}]},
                {"id": "main", "refs": [{"headline": "Take-1", "slugline": "Take-1", "residRef": "123", "sequence": 1, "is_published": true},
                                        {"headline": "Take-2", "slugline": "Take-2", "residRef": "234", "sequence": 2, "is_published": true}]}
               ],
      "item_id": "345", "guid": "345", "type": "composite", "package_type": "takes", "sequence": 2, "_current_version": 2,
      "state": "published", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
    ]
    """
    When we delete "/archived/123:2"
    Then we get error 400
    """
    {"_message": "Can't kill as article is part of a Package"}
    """

  @auth
  Scenario: Killing an article isn't allowed if all the takes are not available in Archived repo
    Given "archived"
    """
    [
     {"item_id": "123", "guid": "123", "type": "text", "headline": "Take-1", "slugline": "Take-1",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "linked_in_packages": [{"package_type" : "takes", "package" : "345"}],
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2},
     {"groups": [{"id": "root", "refs": [{"idRef": "main"}]},
                {"id": "main", "refs": [{"headline": "Take-1", "slugline": "Take-1", "residRef": "123", "sequence": 1, "is_published": true},
                                        {"headline": "Take-2", "slugline": "Take-2", "residRef": "234", "sequence": 2, "is_published": true}]}
               ],
      "item_id": "345", "guid": "345", "type": "composite", "package_type": "takes", "sequence": 2, "_current_version": 2,
      "state": "published", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
    ]
    """
    When we delete "/archived/123:2"
    Then we get error 400
    """
    {"_message": "Can't kill as article is part of a Package"}
    """

  @auth
  Scenario: Killing an article isn't allowed if any of the takes is part of a package
    Given "archived"
    """
    [
     {"item_id": "123", "guid": "123", "type": "text", "headline": "Take-1", "slugline": "Take-1",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "linked_in_packages": [{"package_type" : "takes", "package" : "345"}],
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2},
     {"item_id": "234", "guid": "234", "type": "text", "headline": "Take-2", "slugline": "Take-2",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "linked_in_packages": [{"package_type" : "takes", "package" : "345"}, {"package" : "456"}],
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2},
     {"groups": [{"id": "root", "refs": [{"idRef": "main"}]},
                {"id": "main", "refs": [{"headline": "Take-1", "slugline": "Take-1", "residRef": "123", "sequence": 1, "is_published": true},
                                        {"headline": "Take-2", "slugline": "Take-2", "residRef": "234", "sequence": 2, "is_published": true}]}
               ],
      "item_id": "345", "guid": "345", "type": "composite", "package_type": "takes", "sequence": 2, "_current_version": 2,
      "state": "published", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}},
     {"groups": [{"id": "root", "refs": [{"idRef": "main"}]},
                {"id": "main", "refs": [{"headline": "headline", "slugline": "slugline", "residRef": "234"}]}
               ],
      "item_id": "456", "guid": "456", "type": "composite", "_current_version": 2, "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
    ]
    """
    When we delete "/archived/123:2"
    Then we get error 400
    """
    {"_message": "Can't kill as article is part of a Package"}
    """

  @auth
  Scenario: Killing an article isn't allowed if article is a Master Story for Broadcast(s)
    Given "archived"
    """
    [
     {"item_id": "123", "guid": "123", "type": "text", "headline": "Take-1", "slugline": "Take-1",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2},
     {"item_id": "234", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "genre" : [{"name" : "Broadcast Script", "qcode" : "Broadcast Script"}], "headline": "broadcast",
      "slugline" : "broadcast", "broadcast" : {"master_id" : "123"}, "type" : "text",
      "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2}
    ]
    """
    When we delete "/archived/123:2"
    Then we get error 400
    """
    {"_message": "Can't kill as this article acts as a Master Story for existing broadcast(s)"}
    """

    @auth
    Scenario: Fails to delete from archived with no privilege
      Given "archived"
      """
      [{"item_id": "123", "guid": "123", "type": "text", "headline": "test", "slugline": "slugline",
        "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}], "state": "published",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body", "_current_version": 2}]
      """
      When we patch "/users/#CONTEXT_USER_ID#"
      """
      {"user_type": "user", "privileges": {"archive": 1, "unlock": 1, "tasks": 1, "users": 1}}
      """
      Then we get OK response
      When we delete "/archived/123:2"
      Then we get response code 403
      When we get "/archived"
      Then we get list with 1 items

  @auth @notification
  Scenario: Kill a Text Article in the Dusty Archive with no takes
    When we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "state": "fetched", "slugline": "archived",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}],
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "dateline" : {
        "located" : {
            "state_code" : "NSW",
            "city" : "Sydney",
            "tz" : "Australia/Sydney",
            "country_code" : "AU",
            "dateline" : "city",
            "alt_name" : "",
            "state" : "New South Wales",
            "city_code" : "Sydney",
            "country" : "Australia"
        },
        "source" : "AAP",
        "date" : "2016-04-13T04:29:14",
        "text" : "SYDNEY April 13 AAP -"
      },
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
    When run import legal publish queue
    And we get "/legal_publish_queue"
    Then we get list with 0 items
    When we transmit items
    And run import legal publish queue
    When we get "/legal_publish_queue"
    Then we get list with 2 items
    """
    {"_items" : [
        {"item_id": "123", "subscriber_id":"Channel 2", "content_type": "text",
        "item_version": 2, "publishing_action": "published"},
        {"item_id": "123", "subscriber_id":"Channel 1", "content_type": "text",
        "item_version": 2, "publishing_action": "published"}
     ]}
    """
    When we expire items
    """
    ["123"]
    """
    And we get "/published"
    Then we get list with 0 items
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 0 items
    When we get "/archived"
    Then we get list with 1 items
    """
    {"_items" : [{"item_id": "123", "state": "published", "type": "text", "_current_version": 2}]}
    """
    When we get "/legal_publish_queue"
    Then we get list with 2 items
    When we patch "/archived/123:2"
    """
    {"body_html": "Killed body.", "operation": "kill"}
    """
    Then we get OK response
    And we get 1 emails
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [{"_id": "123", "state": "killed", "type": "text", "_current_version": 3, "queue_state": "queued"}]}
    """
    When we transmit items
    And run import legal publish queue
    And we get "/legal_publish_queue"
    Then we get list with 4 items
    """
    {"_items" : [
        {"item_id": "123", "subscriber_id":"Channel 2", "content_type": "text",
        "item_version": 2, "publishing_action": "published"},
        {"item_id": "123", "subscriber_id":"Channel 2", "content_type": "text",
        "item_version": 3, "publishing_action": "killed"},
        {"item_id": "123", "subscriber_id":"Channel 1", "content_type": "text",
        "item_version": 2, "publishing_action": "published"},
        {"item_id": "123", "subscriber_id":"Channel 1", "content_type": "text",
        "item_version": 3, "publishing_action": "killed"}
     ]}
    """
    When we get "/archive/123"
    Then we get OK response
    And we get text "Please kill story slugged archived" in response field "body_html"
    And we get text "Killed body" in response field "body_html"
    When we get "/archived/123:2"
    Then we get error 404
    When we get "/archived"
    Then we get list with 0 items
    When we get "/legal_archive/123"
    Then we get existing resource
    """
    {"_id": "123", "type": "text", "_current_version": 3, "state": "killed", "pubstatus": "canceled", "operation": "kill"}
    """
    When we get "/legal_archive/123?version=all"
    Then we get list with 3 items
    When we expire items
    """
    ["123"]
    """
    And we get "/published"
    Then we get list with 0 items
    When we get "/archive"
    Then we get list with 0 items

  @auth @notification
  Scenario: Takedown a Text Article in the Dusty Archive
    When we post to "/subscribers" with "api" and success
    """
    {
      "name":"Channel api", "media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "api_products": ["#products._id#"]
    }
    """
    And we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "state": "fetched", "slugline": "archived",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}],
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "target_types": [{"qcode": "digital", "allow": false}],
      "dateline" : {
        "located" : {
            "state_code" : "NSW",
            "city" : "Sydney",
            "tz" : "Australia/Sydney",
            "country_code" : "AU",
            "dateline" : "city",
            "alt_name" : "",
            "state" : "New South Wales",
            "city_code" : "Sydney",
            "country" : "Australia"
        },
        "source" : "AAP",
        "date" : "2016-04-13T04:29:14",
        "text" : "SYDNEY April 13 AAP -"
      },
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
    When run import legal publish queue
    And we get "/legal_publish_queue"
    Then we get list with 1 items
    """
    {"_items" : [
        {"item_id": "123", "subscriber_id":"Channel api", "content_type": "text",
        "item_version": 2, "publishing_action": "published"}
     ]}
    """
    When we transmit items
    And run import legal publish queue
    When we get "/legal_publish_queue"
    Then we get list with 2 items
    """
    {"_items" : [
        {"item_id": "123", "subscriber_id":"Channel api", "content_type": "text",
        "item_version": 2, "publishing_action": "published"},
        {"item_id": "123", "subscriber_id":"Channel 2", "content_type": "text",
        "item_version": 2, "publishing_action": "published"}
     ]}
    """
    When we expire items
    """
    ["123"]
    """
    And we get "/published"
    Then we get list with 0 items
    When we enqueue published
    And we get "/publish_queue"
    Then we get list with 0 items
    When we get "/archived"
    Then we get list with 1 items
    """
    {"_items" : [{"item_id": "123", "state": "published", "type": "text", "_current_version": 2}]}
    """
    When we get "/legal_publish_queue"
    Then we get list with 2 items
    When we patch "/archived/123:2"
    """
    {"body_html": "Takedown body.", "operation": "takedown"}
    """
    Then we get OK response
    And we get 1 emails
    When we get "/published"
    Then we get list with 1 items
    """
    {"_items" : [{"_id": "123", "state": "recalled", "type": "text", "_current_version": 3, "queue_state": "queued"}]}
    """
    When we transmit items
    And run import legal publish queue
    And we get "/legal_publish_queue"
    Then we get list with 4 items
    """
    {"_items" : [
        {"item_id": "123", "subscriber_id":"Channel api", "content_type": "text",
        "item_version": 2, "publishing_action": "published"},
        {"item_id": "123", "subscriber_id":"Channel 2", "content_type": "text",
        "item_version": 2, "publishing_action": "published"},
        {"item_id": "123", "subscriber_id":"Channel api", "content_type": "text",
        "item_version": 3, "publishing_action": "recalled"},
        {"item_id": "123", "subscriber_id":"Channel 2", "content_type": "text",
        "item_version": 3, "publishing_action": "recalled"}
     ]}
    """
    When we get "/archive/123"
    Then we get OK response
    And we get text "Please takedown story slugged archived" in response field "body_html"
    And we get text "Takedown body" in response field "body_html"
    And we get emails
    """
    [
      {"body": "Please takedown story slugged archived"},
      {"body": "Takedown body"}
    ]
    """
    When we get "/archived/123:2"
    Then we get error 404
    When we get "/archived"
    Then we get list with 0 items
    When we get "/legal_archive/123"
    Then we get existing resource
    """
    {"_id": "123", "type": "text", "_current_version": 3, "state": "recalled", "pubstatus": "canceled", "operation": "takedown"}
    """
    When we get "/legal_archive/123?version=all"
    Then we get list with 3 items
    When we expire items
    """
    ["123"]
    """
    And we get "/published"
    Then we get list with 0 items
    When we get "/archive"
    Then we get list with 0 items

  @auth @notification
  Scenario: Takedown a Text Article that exists only in Archived
    Given "archived" with objectid
    """
    [{
      "_id": "56aad5a61d41c8aa98ddd015", "guid": "123", "item_id": "123", "_current_version": "1", "type": "text", "abstract": "test", "state": "fetched", "slugline": "slugline",
      "headline": "headline", "anpa_category" : [{"qcode" : "e", "name" : "Entertainment"}],
      "flags" : {"marked_archived_only": true},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body"
    }]
    """
    When we patch "/archived/56aad5a61d41c8aa98ddd015"
    """
    {"operation": "takedown"}
    """
    When we get "/archived"
    Then we get list with 0 items
    And we get 1 emails