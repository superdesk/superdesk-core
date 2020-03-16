Feature: Link content

    @auth @test
    Scenario: Unlink an update of an unpublished story
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{
              "guid": "123",
              "type": "text",
              "headline": "test1",
              "slugline": "comics",
              "state": "fetched",
              "subject":[{"qcode": "17004000", "name": "Statistics"}],
              "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
              "body_html": "Story-1"
        }]
        """
        When we rewrite "123"
        """
            {"desk_id": "#desks._id#"}
        """
        When we get "/archive/#REWRITE_ID#"
        Then we get existing resource
        """
        {
            "_id": "#REWRITE_ID#",
            "rewrite_of": "123",
            "headline": "test1",
            "rewrite_sequence": 1,
            "anpa_take_key": "update"
        }
        """
        When we get "/archive/123"
        Then we get existing resource
        """
        {
            "_id": "123",
            "rewritten_by": "#REWRITE_ID#"
        }
        """
        When we delete link "archive/#REWRITE_ID#/rewrite"
        Then we get response code 204
        When we get "/archive/#REWRITE_ID#"
        Then we get "rewrite_of" not populated
        And we get "anpa_take_key" not populated
        And we get "rewrite_sequence" not populated
        When we get "/archive/123"
        Then we get "rewritten_by" not populated

    @auth
    Scenario: Unlink an update of a published story
        Given "desks"
        """
        [{"name": "Sports"}]
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
        }
        ]
        """
        And "archive"
        """
        [{
              "guid": "123",
              "type": "text",
              "headline": "test1",
              "slugline": "comics",
              "state": "fetched",
              "subject":[{"qcode": "17004000", "name": "Statistics"}],
              "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
              "body_html": "Story-1"
        }]
        """
        When we publish "123" with "publish" type and "published" state
        Then we get OK response
        When we rewrite "123"
        """
            {"desk_id": "#desks._id#"}
        """
        When we get "/archive/#REWRITE_ID#"
        Then we get existing resource
        """
        {
            "_id": "#REWRITE_ID#",
            "rewrite_of": "123",
            "headline": "test1",
            "rewrite_sequence": 1,
            "anpa_take_key": "update"
        }
        """
        When we get "/archive/123"
        Then we get existing resource
        """
        {
            "_id": "123",
            "rewritten_by": "#REWRITE_ID#"
        }
        """
        When we delete link "archive/#REWRITE_ID#/rewrite"
        Then we get response code 204
        When we get "/archive/#REWRITE_ID#"
        Then we get "rewrite_of" not populated
        And we get "anpa_take_key" not populated
        And we get "rewrite_sequence" not populated
        When we get "/archive/123"
        Then we get "rewritten_by" not populated
        When we get "/published/123"
        Then we get "rewritten_by" not populated


    @auth
    Scenario: Unlink ignores item in a normal package
        Given empty "archive"
        And "desks"
        """
        [{"name": "test desk"}]
        """
        When we post to "archive" with success
        """
        [{"headline": "test", "guid": "123", "slugline": "WORMS"},
         {"headline": "test", "guid": "456", "slugline": "SNAILS"}]
        """
        When we post to "archive" with success
        """
        {
            "groups": [
                {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                {
                    "id": "main",
                    "refs": [
                        {
                            "headline": "test package with text",
                            "residRef": "123",
                            "slugline": "WORMS"
                        },
                        {
                            "headline": "test package with text",
                            "residRef": "456",
                            "slugline": "SNAILS"
                        }
                    ],
                    "role": "grpRole:Main"
                }
            ],
            "guid": "789",
            "type": "composite",
            "task": {"user": "#user._id#", "desk": "#desks._id#"}
        }
        """
        When we delete link "archive/456/rewrite"
        Then we get error 400
        """
        {"_message": "Only updates can be unlinked!"}
        """

