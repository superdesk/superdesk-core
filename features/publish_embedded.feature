Feature: Publish embedded items feature
  Background: Setup data
    Given "desks"
    """
    [{"name": "Sports", "members": [{"user": "#CONTEXT_USER_ID#"}], "source": "foo"}]
    """
    And "validators"
    """
    [
        {
            "_id": "publish_text",
            "act": "publish",
            "type": "text",
            "schema": {
                "headline": {"type": "string",
                    "required": true,
                    "nullable": false,
                    "empty": false,
                    "maxlength": 42
                }
            }
        },
        {
            "_id": "publish_embedded_picture",
            "act": "publish",
            "type": "picture",
            "embedded": true,
            "schema": {
                "type": {
                    "type": "string",
                    "required": true,
                    "allowed": ["picture"]
                },
                "pubstatus": {
                    "type": "string",
                    "required": true,
                    "allowed": ["usable"]
                },
                "slugline": {
                    "type": "string",
                    "required": true,
                    "nullable": false,
                    "empty": false,
                    "maxlength": 24
                }
            }
        },
        {
            "_id": "correct_text",
            "act": "correct",
            "type": "text",
            "schema": {
                "headline": {"type": "string",
                    "required": true,
                    "nullable": false,
                    "empty": false,
                    "maxlength": 42
                }
            }
        },
        {
            "_id": "correct_embedded_picture",
            "act": "correct",
            "type": "picture",
            "embedded": true,
            "schema": {
                "type": {
                    "type": "string",
                    "required": true,
                    "allowed": ["picture"]
                },
                "pubstatus": {
                    "type": "string",
                    "required": true,
                    "allowed": ["usable"]
                },
                "slugline": {
                    "type": "string",
                    "required": true,
                    "nullable": false,
                    "empty": false,
                    "maxlength": 24
                }
            }
        }
    ]
    """
    And "filter_conditions"
    """
    [
    {"_id": "source-foo", "name": "source-foo", "field": "source", "operator": "eq", "value": "foo"},
    {"_id": "source-aap", "name": "source-aap", "field": "source", "operator": "eq", "value": "AAP"},
    {"_id": "type-text", "name": "type-text", "field": "type", "operator": "eq", "value": "text"},
    {"_id": "type-picture", "name": "type-picture", "field": "type", "operator": "eq", "value": "picture"}
    ]
    """
    And "content_filters"
    """
    [
    {"content_filter": [{"expression": {"fc": ["source-foo", "type-text"]}}], "name": "text-source-foo", "_id": "text-source-foo"},
    {"content_filter": [{"expression": {"fc": ["source-aap", "type-picture"]}}], "name": "pic-source-aap", "_id": "pic-source-aap"},
    {"content_filter": [{"expression": {"fc": ["type-text"]}}], "name": "type-text", "_id": "type-text"},
    {"content_filter": [{"expression": {"fc": ["type-picture"]}}], "name": "type-picture", "_id": "type-picture"}
    ]
    """
    And "products"
    """
    [{"_id": "text-source-foo", "name":"text-source-foo",
     "content_filter":{"filter_id":"text-source-foo", "filter_type": "permitting"}, "product_type": "both"},
     {"_id": "pic-source-aap", "name":"pic-source-aap",
     "content_filter":{"filter_id":"pic-source-aap", "filter_type": "permitting"}, "product_type": "both"},
     {"_id": "58f6120488ea94d000369a32", "name":"type-text",
     "content_filter":{"filter_id":"type-text", "filter_type": "permitting"}, "product_type": "both"},
     {"_id": "type-picture", "name":"type-picture",
     "content_filter":{"filter_id":"type-picture", "filter_type": "permitting"}, "product_type": "both"}
    ]
    """
    And "subscribers"
    """
    [{
      "_id": "58f6110d88ea94d000369a2f",
      "name":"Channel 1",
      "media_type": "media",
      "subscriber_type": "all",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["text-source-foo"],
      "codes": "Aaa",
      "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}],
      "api_products": ["text-source-foo"]
    },
    {
      "_id": "58f6113988ea94d000369a30",
      "name":"Channel 2",
      "media_type":"media",
      "subscriber_type": "all",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["pic-source-aap"],
      "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
    },
    {
      "_id": "58f6115b88ea94d000369a31",
      "name":"Channel 3",
      "media_type":"media",
      "subscriber_type": "all",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "api_products": ["58f6120488ea94d000369a32", "type-picture"]
    }]
    """
    And "vocabularies"
    """
    [{"_id": "crop_sizes", "items": [{"is_active": true, "name": "3:2", "width": 3, "height": 2}]}]
    """

    @auth
    @vocabulary
    Scenario: Publish embedded picture together with text item - no other ops
        When we post to "archive"
        """
        {"type": "text", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}, "guid": "foo"}
        """
        Then we get OK response
        When we upload a file "bike.jpg" to "archive"
        And we patch "/archive/#archive._id#"
        """
        {"task": {"desk": "#desks._id#"}, "headline": "test"}
        """
        And we patch "/archive/#archive._id#"
        """
        {"state": "in_progress"}
        """
        Then we get OK response

        When we patch "archive/foo"
        """
        {
            "headline": "foo",
            "slugline": "bar",
            "state": "in_progress",
            "associations": {
                "embedded1": {
                    "_id": "#archive._id#",
                    "type": "picture",
                    "headline": "test",
                    "alt_text": "alt_text",
                    "description_text": "description_text",
                    "state": "in_progress"
                }
            }
        }
        """
        Then we get OK response

        When we publish "foo" with "publish" type and "published" state
        Then we get error 400
        """
        {"_issues": {"validator exception": "['Associated item  test: SLUGLINE is a required field']"}}
        """

        When we patch "archive/#archive._id#"
        """
        {"slugline": "bike", "pubstatus" : "usable"}
        """
        Then we get OK response

        When we publish "foo" with "publish" type and "published" state
        """
        {"headline": "foo", "associations": {
            "embedded1": {
                "_id": "#archive._id#",
                "slugline": "bike",
                "pubstatus" : "usable",
                "type": "picture",
                "headline": "test",
                "alt_text": "alt_text",
                "description_text": "description_text",
                "state": "in_progress"}}}
        """
        Then we get OK response
        When we get "published"
        Then we get list with 2 items
        When we get "publish_queue"
        Then we get list with 4 items
        """
        {"_items": [
        {"subscriber_id": "58f6115b88ea94d000369a31", "headline": "test", "destination": {"delivery_type" : "content_api"}},
        {"subscriber_id": "58f6115b88ea94d000369a31", "item_id": "foo", "destination": {"delivery_type" : "content_api"}},
        {"subscriber_id": "58f6110d88ea94d000369a2f", "item_id": "foo", "destination": {"delivery_type" : "content_api"}},
        {"subscriber_id": "58f6110d88ea94d000369a2f", "item_id": "foo", "destination": {"delivery_type" : "email"}}
        ]}
        """
        When we get "/items/foo"
        Then we get OK response
        Then we assert the content api item "foo" is published to subscriber "58f6110d88ea94d000369a2f"
        Then we assert the content api item "foo" is published to subscriber "58f6115b88ea94d000369a31"
        Then we assert the content api item "foo" is not published to subscriber "58f6113988ea94d000369a30"
        Then we assert content api item "foo" with associated item "embedded1" is published to "58f6115b88ea94d000369a31"
        Then we assert content api item "foo" with associated item "embedded1" is not published to "58f6110d88ea94d000369a2f"

    @auth
    @vocabulary
    Scenario: Publish embedded picture together with text item and correct the item
        When we post to "archive"
        """
        {"type": "text", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}, "guid": "foo"}
        """
        Then we get OK response
        When we upload a file "bike.jpg" to "archive"
        And we patch "/archive/#archive._id#"
        """
        {"task": {"desk": "#desks._id#"}, "headline": "test"}
        """
        And we patch "/archive/#archive._id#"
        """
        {"state": "in_progress"}
        """
        Then we get OK response

        When we patch "archive/foo"
        """
        {
            "headline": "foo",
            "slugline": "bar",
            "state": "in_progress",
            "associations": {
                "embedded1": {
                    "_id": "#archive._id#",
                    "type": "picture",
                    "headline": "test",
                    "alt_text": "alt_text",
                    "description_text": "description_text",
                    "state": "in_progress"
                }
            }
        }
        """
        Then we get OK response

        When we publish "foo" with "publish" type and "published" state
        Then we get error 400
        """
        {"_issues": {"validator exception": "['Associated item  test: SLUGLINE is a required field']"}}
        """

        When we patch "archive/#archive._id#"
        """
        {"slugline": "bike", "pubstatus" : "usable"}
        """
        Then we get OK response

        When we publish "foo" with "publish" type and "published" state
        """
        {"headline": "foo", "associations": {
            "embedded1": {
                "_id": "#archive._id#",
                "type": "picture",
                "slugline": "bike",
                "pubstatus" : "usable",
                "headline": "test",
                "alt_text": "alt_text",
                "description_text": "description_text",
                "state": "in_progress"}}}
        """
        Then we get OK response
        When we get "published"
        Then we get list with 2 items
        When we get "publish_queue"
        Then we get list with 4 items
        """
        {"_items": [
        {"subscriber_id": "58f6115b88ea94d000369a31", "headline": "test", "destination": {"delivery_type" : "content_api"}},
        {"subscriber_id": "58f6115b88ea94d000369a31", "item_id": "foo", "destination": {"delivery_type" : "content_api"}},
        {"subscriber_id": "58f6110d88ea94d000369a2f", "item_id": "foo", "destination": {"delivery_type" : "content_api"}},
        {"subscriber_id": "58f6110d88ea94d000369a2f", "item_id": "foo", "destination": {"delivery_type" : "email"}}
        ]}
        """
        When we get "/items/foo"
        Then we get OK response
        Then we assert the content api item "foo" is published to subscriber "58f6110d88ea94d000369a2f"
        Then we assert the content api item "foo" is published to subscriber "58f6115b88ea94d000369a31"
        Then we assert the content api item "foo" is not published to subscriber "58f6113988ea94d000369a30"
        Then we assert content api item "foo" with associated item "embedded1" is published to "58f6115b88ea94d000369a31"
        Then we assert content api item "foo" with associated item "embedded1" is not published to "58f6110d88ea94d000369a2f"
        When we patch "/subscribers/58f6115b88ea94d000369a31"
        """
        {"api_products": ["58f6120488ea94d000369a32"]}
        """
        Then we get OK response
        When we publish "foo" with "correct" type and "corrected" state
        """
        {"headline": "foo corrected"}
        """
        Then we get OK response
        When we get "published"
        Then we get list with 4 items
        When we get "publish_queue"
        Then we get list with 8 items
        When we get "/items/foo"
        Then we get OK response
        Then we assert the content api item "foo" is published to subscriber "58f6110d88ea94d000369a2f"
        Then we assert the content api item "foo" is published to subscriber "58f6115b88ea94d000369a31"
        Then we assert the content api item "foo" is not published to subscriber "58f6113988ea94d000369a30"
        Then we assert content api item "foo" with associated item "embedded1" is published to "58f6115b88ea94d000369a31"
        Then we assert content api item "foo" with associated item "embedded1" is not published to "58f6110d88ea94d000369a2f"

        When we publish "foo" with "correct" type and "corrected" state
        """
        {"headline": "foo corrected v2"}
        """
        Then we get OK response
        When we get "published"
        Then we get list with 6 items

    @auth
    @vocabulary
    Scenario: Publish embedded picture together with text item and resend to another subscriber
        When we post to "archive"
        """
        {"type": "text", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}, "guid": "foo"}
        """
        Then we get OK response
        When we upload a file "bike.jpg" to "archive"
        And we patch "/archive/#archive._id#"
        """
        {"task": {"desk": "#desks._id#"}, "headline": "test"}
        """
        And we patch "/archive/#archive._id#"
        """
        {"state": "in_progress"}
        """
        Then we get OK response

        When we patch "archive/foo"
        """
        {
            "headline": "foo",
            "slugline": "bar",
            "state": "in_progress",
            "associations": {
                "embedded1": {
                    "_id": "#archive._id#",
                    "type": "picture",
                    "pubstatus" : "usable",
                    "headline": "test",
                    "alt_text": "alt_text",
                    "description_text": "description_text",
                    "state": "in_progress"
                }
            }
        }
        """
        Then we get OK response

        When we publish "foo" with "publish" type and "published" state
        Then we get error 400
        """
        {"_issues": {"validator exception": "['Associated item  test: SLUGLINE is a required field']"}}
        """

        When we patch "archive/#archive._id#"
        """
        {"slugline": "bike", "pubstatus" : "usable"}
        """
        Then we get OK response

        When we publish "foo" with "publish" type and "published" state
        """
        {"headline": "foo", "associations": {
            "embedded1": {
                "_id": "#archive._id#",
                "type": "picture",
                "headline": "test",
                "slugline": "bike",
                "pubstatus" : "usable",
                "alt_text": "alt_text",
                "description_text": "description_text",
                "state": "in_progress"}}}
        """
        Then we get OK response
        When we get "published"
        Then we get list with 2 items
        When we get "publish_queue"
        Then we get list with 4 items
        """
        {"_items": [
        {"subscriber_id": "58f6115b88ea94d000369a31", "headline": "test", "destination": {"delivery_type" : "content_api"}},
        {"subscriber_id": "58f6115b88ea94d000369a31", "item_id": "foo", "destination": {"delivery_type" : "content_api"}},
        {"subscriber_id": "58f6110d88ea94d000369a2f", "item_id": "foo", "destination": {"delivery_type" : "content_api"}},
        {"subscriber_id": "58f6110d88ea94d000369a2f", "item_id": "foo", "destination": {"delivery_type" : "email"}}
        ]}
        """
        When we get "/items/foo"
        Then we get OK response
        Then we assert the content api item "foo" is published to subscriber "58f6110d88ea94d000369a2f"
        Then we assert the content api item "foo" is published to subscriber "58f6115b88ea94d000369a31"
        Then we assert the content api item "foo" is not published to subscriber "58f6113988ea94d000369a30"
        Then we assert content api item "foo" with associated item "embedded1" is published to "58f6115b88ea94d000369a31"
        Then we assert content api item "foo" with associated item "embedded1" is not published to "58f6110d88ea94d000369a2f"
        When we post to "subscribers" with "sub-4" and success
        """
        [{
          "name":"Channel 4",
          "media_type":"media",
          "subscriber_type": "wire",
          "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "api_products": ["58f6120488ea94d000369a32"]
        }]
        """
        Then we get OK response
        When we post to "/archive/foo/resend"
        """
        {
          "subscribers": ["#subscribers._id#"],
          "version": 3
        }
        """
        Then we get OK response
        When we get "/items/foo"
        Then we get OK response
        Then we assert the content api item "foo" is published to subscriber "58f6110d88ea94d000369a2f"
        Then we assert the content api item "foo" is published to subscriber "58f6115b88ea94d000369a31"
        Then we assert the content api item "foo" is published to subscriber "#subscribers._id#"
        Then we assert the content api item "foo" is not published to subscriber "58f6113988ea94d000369a30"
        Then we assert content api item "foo" with associated item "embedded1" is published to "58f6115b88ea94d000369a31"
        Then we assert content api item "foo" with associated item "embedded1" is published to "#subscribers._id#"
        Then we assert content api item "foo" with associated item "embedded1" is not published to "58f6110d88ea94d000369a2f"

    @auth
    @vocabulary
    Scenario: Publish embedded picture together with text item with copy metadata from text item
        When we post to "archive"
        """
        {
            "type": "text",
            "task": {"desk": "#desks._id#"},
            "guid": "foo",
            "slugline": "text item slugline",
            "anpa_category": [{"qcode": "a", "name": "foo"}],
            "subject": [{"qcode": "01000000", "name": "bar"}],
            "urgency": 1,
            "priority": 2
        }
        """
        Then we get OK response

        When we upload a file "bike.jpg" to "archive"
        And we patch "/archive/#archive._id#"
        """
        {"task": {"desk": "#desks._id#"}}
        """
        And we patch "/archive/#archive._id#"
        """
        {"state": "in_progress", "subject": [{"qcode": "02000000", "name": "xxx"}]}
        """
        Then we get OK response

        When we patch "archive/foo"
        """
        {
            "headline": "foo",
            "state": "in_progress",
            "associations": {
                "embedded1": {
                    "_id": "#archive._id#",
                    "type": "picture",
                    "headline": "test",
                    "alt_text": "alt_text",
                    "description_text": "description_text",
                    "state": "in_progress",
                    "subject": [{"qcode": "02000000", "name": "xxx"}]
                }
            }
        }
        """
        Then we get OK response

        When we publish "foo" with "publish" type and "published" state
        Then we get error 400
        """
        {"_issues": {"validator exception": "['Associated item  #archive._id#: SLUGLINE is a required field']"}}
        """
        Then we set copy metadata from parent flag
        When we publish "foo" with "publish" type and "published" state
        Then we get updated response
        """
        {
            "headline": "foo",
            "associations": {
                "embedded1": {
                    "_id": "#archive._id#",
                    "slugline": "text item slugline",
                    "type": "picture",
                    "headline": "test",
                    "alt_text": "alt_text",
                    "description_text": "description_text",
                    "state": "published",
                    "subject": [{"qcode": "01000000", "name": "bar"}],
                    "anpa_category": [{"qcode": "a", "name": "foo"}],
                    "urgency": 1,
                    "priority": 2
                }
            }
        }
        """
