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
