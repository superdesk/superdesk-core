Feature: Rundowns

    @auth
    Scenario: Show CRUD
        When we post to "/rundown_shows"
        """
        {"name": "Test", "description": "Test description", "duration": 10.5}
        """
        Then we get response code 201

        When we get "/rundown_shows"
        Then we get list with 1 items
        """
        {"_items": [{"name": "Test"}]}
        """

        When we get "/rundown_shows/#rundown_shows._id#"
        Then we get existing resource
        """
        {"name": "Test", "description": "Test description", "duration": 10.5}
        """

        When we patch "/rundown_shows/#rundown_shows._id#"
        """
        {"name": "Updated", "duration": 11.1}
        """
        Then we get OK response

        When we delete "/rundown_shows/#rundown_shows._id#"
        Then we get OK response

        When we get "/rundown_shows"
        Then we get list with 0 items


    @auth
    Scenario: Templates CRUD
        Given "rundown_shows"
        """
        [{"name": "Test"}]
        """

        When we post to "/rundown_templates"
        """
        {
            "show": "#rundown_shows._id#",
            "name": "test template",
            "air_time": "06:00",
            "headline_template": {
                "prefix": "Marker",
                "separator": "||",
                "date_format": "dd.MM.yyyy"
            }
        }
        """
        Then we get response code 201

        When we patch "/rundown_templates/#rundown_templates._id#"
        """
        {"schedule": {"is_active": true, "day_of_week": ["MON", "FRI"]}}
        """
        Then we get OK response

        When we get "/rundown_templates"
        Then we get list with 1 items
        """
        {"_items": [{"schedule": {"is_active": true}}]}
        """

        When we delete "/rundown_templates/#rundown_templates._id#"
        Then we get OK response

        When we get "/rundown_templates"
        Then we get list with 0 items

    @auth
    Scenario: Rundown context
        When we post to "archive"
        """
        {"headline": "test", "context": "rundowns", "duration": 60}
        """
        Then we get OK response

        When we get "archive"
        Then we get list with 0 items

        When we get "search"
        Then we get list with 0 items

        When we get "archive?context=rundowns"
        Then we get list with 1 items
        """
        {"_items": [
            {"duration": 60}
        ]}
        """
