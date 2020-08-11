Feature: Custom item schema field

    @auth
    Scenario: Register custom field
        When we post to "archive"
        """
        {"type": "text", "custom_field": "foo"}
        """
        Then we get error 400

        When we register custom schema field "custom_field"
        """
        {"type": "string"}
        """
        And we post to "archive"
        """
        {"type": "text", "custom_field": "foo"}
        """
        Then we get new resource

        When we get "/archive/#archive._id#"
        Then we get existing resource
        """
        {"custom_field": "foo"}
        """

        When we get "/archive"
        Then we get list with 1 items
        """
        {"_items": [
            {"custom_field": "foo"}
        ]}
        """

        When we patch "/archive/#archive._id#"
        """
        {"custom_field": "bar"}
        """
        And we get "/archive"
        Then we get list with 1 items
        """
        {"_items": [
            {"custom_field": "bar"}
        ]}
        """

    @auth
    Scenario: Copy custom field on rewrite
        Given "desks"
        """
        [{"name": "sports"}]
        """

        When we register custom schema field "custom_field"
        """
        {"type": "string"}
        """

        When we post to "archive"
        """
        {"guid": "123", "type": "text", "custom_field": "foo", "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#"}}
        """
        Then we get new resource

        When we rewrite "123"
        """
        {"desk_id": "#desks._id#"}
        """
        And we get "/archive/#REWRITE_ID#"
        Then we get existing resource
        """
        {"custom_field": "foo"}
        """

    @auth