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
            "airtime_date": "2050-06-22",
            "headline_template": {
                "prefix": "Marker",
                "separator": "//",
                "date_format": "dd.mm.yy"
            },
            "repeat": true,
            "schedule": {
                "freq": "DAILY",
                "interval": 1,
                "month": [1],
                "monthday": [1, -1],
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
            },
            "airtime_date": "2050-06-22",
            "airtime_time": "06:00"
        }
        """

        When we patch "/shows/#shows._id#/templates/#templates._id#"
        """
        {"schedule": {"weekday": [5, 6]}, "repeat": false}
        """
        Then we get OK response

        When we get "/shows/#shows._id#/templates"
        Then we get list with 1 items
        """
        {"_items": [{"schedule": {"weekday": [5, 6]}, "repeat": false}]}
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
    
    @auth
    Scenario: Validate airtime date when creating/updating template
        Given "shows"
        """
        [
            {"name": "Test"}
        ]
        """

        When we post to "shows/#shows._id#/templates"
        """
        {
            "name": "Test",
            "airtime_time": "06:00",
            "airtime_date": "2022-06-20"
        }
        """
        Then we get error 400
        """
        {"error": "Airtime must be in the future."}
        """

        When we post to "shows/#shows._id#/templates"
        """
        {
            "name": "Test",
            "airtime_time": "06:00",
            "airtime_date": "2050-01-01"
        }
        """
        Then we get new resource
        """
        {"scheduled_on": "2050-01-01T05:00:00+0000"}
        """

        When we patch "shows/#shows._id#/templates/#templates._id#"
        """
        {"airtime_date": "2022-06-20"}
        """
        Then we get error 400
        """
        {"_issues": {"validator exception": "Airtime must be in the future."}}
        """

    @auth
    Scenario: Create rundown based on template schedule
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
                "name": "Scheduled",
                "show": "#shows._id#",
                "airtime_time": "06:00",
                "airtime_date": "2030-01-01",
                "planned_duration": 3600,
                "repeat": true,
                "schedule": {
                    "freq": "DAILY"
                },
                "headline_template": {
                    "prefix": "Scheduled",
                    "separator": "//",
                    "date_format": "%d.%m.%Y"
                }
            },
            {
                "name": "Not Scheduled",
                "show": "#shows._id#",
                "airtime_time": "06:00",
                "airtime_date": "2030-01-01",
                "planned_duration": 3600,
                "repeat": false,
                "schedule": {
                    "freq": "DAILY"
                },
                "headline_template": {
                    "prefix": "Not Scheduled",
                    "separator": "//",
                    "date_format": "%d.%m.%Y"
                }
            }
        ]
        """

        When we run task "apps.rundowns.tasks.create_scheduled_rundowns"
        And we get "archive?scope=rundowns"
        Then we get list with 1 items
        """
        {"_items": [
            {"headline": "Scheduled // 01.01.2030", "rundown_scheduled_on": "2030-01-01T05:00:00+0000"}
        ]}
        """

        When we run task "apps.rundowns.tasks.create_scheduled_rundowns"
        And we get "archive?scope=rundowns"
        Then we get list with 2 items
        """
        {"_items": [
            {"headline": "Scheduled // 01.01.2030", "rundown_scheduled_on": "2030-01-01T05:00:00+0000"},
            {"headline": "Scheduled // 02.01.2030", "rundown_scheduled_on": "2030-01-02T05:00:00+0000"}
        ]}
        """