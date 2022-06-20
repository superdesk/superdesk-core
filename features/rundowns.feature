Feature: Rundowns

    @auth
    Scenario: Show CRUD
        When we post to "/shows"
        """
        {"name": "Test", "description": "Test description", "planned_duration": 10.5}
        """
        Then we get response code 201

        When we get "/shows"
        Then we get list with 1 items
        """
        {"_items": [{"name": "Test"}]}
        """

        When we get "/shows/#shows._id#"
        Then we get existing resource
        """
        {"name": "Test", "description": "Test description", "planned_duration": 10.5}
        """

        When we patch "/shows/#shows._id#"
        """
        {"name": "Updated", "planned_duration": 11.1}
        """
        Then we get OK response

        When we delete "/shows/#shows._id#"
        Then we get OK response

        When we get "/shows"
        Then we get list with 0 items

    @auth
    Scenario: Templates CRUD
        Given "shows"
        """
        [{"name": "Test"}]
        """

        When we post to "/shows/#shows._id#/templates"
        """
        {
            "name": "test template",
            "airtime_time": "06:00",
            "headline_template": {
                "prefix": "Marker",
                "separator": "//",
                "date_format": "dd.mm.yy"
            },
            "schedule": {
                "is_active": true,
                "freq": "DAILY",
                "interval": 1,
                "month": [1],
                "monthday": [1],
                "weekday": [1]
            }
        }
        """
        Then we get new resource
        """
        {
            "_links": {
                "self": {
                    "href": "/shows/#shows._id#/templates/#templates._id#"
                }
            }
        }
        """

        When we patch "/shows/#shows._id#/templates/#templates._id#"
        """
        {"schedule": {"is_active": true, "weekday": [5, 6]}}
        """
        Then we get OK response

        When we get "/shows/#shows._id#/templates"
        Then we get list with 1 items
        """
        {"_items": [{"schedule": {"is_active": true}}]}
        """

        When we delete "/shows/#shows._id#/templates/#templates._id#"
        Then we get OK response

        When we get "/shows/#shows._id#/templates"
        Then we get list with 0 items

    @auth
    Scenario: Rundown scope
        When we post to "archive"
        """
        {"headline": "test", "scope": "rundowns", "planned_duration": 60}
        """
        Then we get OK response

        When we get "archive"
        Then we get list with 0 items

        When we get "search"
        Then we get list with 0 items

        When we get "archive?scope=rundowns"
        Then we get list with 1 items
        """
        {"_items": [
            {"planned_duration": 60}
        ]}
        """
    
    @auth
    Scenario: Create rundown using template
        Given "shows"
        """
        [
            {"name": "Test"}
        ]
        """
        And "rundown_templates"
        """
        [
            {
                "name": "Test",
                "show": "#shows._id#",
                "headline": "Marker",
                "airtime_time": "06:00",
                "planned_duration": 3600,
                "headline_template": {
                    "prefix": "Marker",
                    "separator": "//",
                    "date_format": "%d.%m.%Y"
                }
            }
        ]
        """

        When we post to "/shows/#shows._id#/rundowns"
        """
        {"template": "#rundown_templates._id#", "airtime_date": "2022-06-10"}
        """
        Then we get new resource
        """
        {
            "show": "#shows._id#",
            "rundown_template": "#rundown_templates._id#",
            "headline": "Marker // 10.06.2022",
            "planned_duration": 3600,
            "airtime_time": "06:00",
            "airtime_date": "2022-06-10",
            "_links": {
                "self": {
                    "href": "archive/#rundowns._id#",
                    "title": "Archive"
                }
            }
        }
        """

        When we get "archive?scope=rundowns"
        Then we get list with 1 items
        """
        {"_items": [
            {"headline": "Marker // 10.06.2022"}
        ]}
        """
