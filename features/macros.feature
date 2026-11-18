Feature: Macros

    @auth
    Scenario: Get list of all macros
        When we get "/macros"
        Then we get list with 2+ items
            """
            {"_items":
                [{"name": "usd_to_cad",
                  "label": "Currency USD to CAD",
                  "description": "Convert USD to CAD."},
                 {"name": "acre_to_metric", "group": "area"}
                ]}
            """

    @auth
    Scenario: Get list of all macros by desk
        When we get "/macros?desk=POLITICS"
        Then we get list with 2+ items
            """
            {"_items": [{"name": "populate_abstract", "label": "Populate Abstract", "description": "Populate the abstract field with the first sentence of the body"}]}
            """

    @auth
    @clean
    Scenario: Get list of updated macros
        Given empty "stages"
        Given "desks"
        """
        [{"name": "Politics"}]
        """
        Given we create a new macro "behave_macro.py"

        When we get "/macros?desk=POLITICS"
        Then we get list with 2+ items
            """
            {"_items": [{"name": "update_fields", "label": "Update Fields", "description": "Updates the abstract field"}]}
            """

    @auth
    Scenario: Trigger macro via name
        When we post to "/macros"
            """
            {"macro": "usd_to_cad",
             "item": {"body_html": "$10 bar", "headline": "foo $5"}}
            """
        Then we get new resource
            """
            {"item": {"body_html": "$10 (CAD 20) bar", "headline": "foo $5 (CAD 10)"},
             "diff": {"$10": "$10 (CAD 20)", "$5": "$5 (CAD 10)"}}
            """

    @auth
    Scenario: Trigger macro and commit
        Given "archive"
            """
            [{"_id": "item1", "guid": "item1", "type": "text"}]
            """

        When we post to "/macros"
            """
            {"macro": "usd_to_cad",
             "item": {"_id": "item1", "body_html": "$10"}, "commit": true}
            """
        Then we get new resource

        When we get "/archive/item1"
        Then we get existing resource
            """
            {"body_html": "$10 (CAD 20)"}
            """

    @auth
    Scenario: Return an error when triggering unknown macro
        When we post to "/macros"
            """
            {"macro": "this does not exist!", "item": {"body_html": "test"}}
            """
        Then we get response code 400

    @auth
    @clean
    Scenario: Auto publish macro publishes the item on stage
        Given the "validators"
            """
            [{"_id": "auto_publish_text", "act": "auto_publish", "type": "text", "schema": {}}]
            """
        And "desks"
            """
            [{"name": "Sports", "members": [{"user": "#CONTEXT_USER_ID#"}]}]
            """
        And "archive"
            """
            [{"guid": "123", "type": "text", "headline": "test", "slugline": "test", "state": "submitted",
              "body_html": "Test body",
              "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
            """
        When we post to "/stages"
            """
            [{"name": "Auto publish", "task_status": "in_progress", "desk": "#desks._id#",
              "onstage_macro": "Auto Publish"}]
            """
        And we post to "/archive/123/move"
            """
            [{"task": {"desk": "#desks._id#", "stage": "#stages._id#"}}]
            """
        Then we get OK response
        And we get etag matching "/archive/123"
        When we get "/archive/123"
        Then we get existing resource
            """
            {"state": "published", "auto_publish": true}
            """
        When we get "/published"
        Then we get list with 1 items
            """
            {"_items": [{"_id": "123", "state": "published", "auto_publish": true}]}
            """

    @auth
    @clean
    Scenario: Auto publish macro can not be run directly
        Given the "validators"
            """
            [{"_id": "auto_publish_text", "act": "auto_publish", "type": "text", "schema": {}}]
            """
        And "desks"
            """
            [{"name": "Sports", "members": [{"user": "#CONTEXT_USER_ID#"}]}]
            """
        And "archive"
            """
            [{"_id": "123", "guid": "123", "type": "text", "headline": "test", "slugline": "test",
              "state": "in_progress", "body_html": "Test body",
              "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
            """
        When we post to "/macros"
            """
            {"macro": "Auto Publish", "item": {"_id": "123"}}
            """
        Then we get error 500
            """
            {"_message": "403: Auto Publish can only run as an on stage macro."}
            """
        When we get "/archive/123"
        Then we get existing resource
            """
            {"state": "in_progress"}
            """
        When we get "/published"
        Then we get list with 0 items
