@wip
Feature: Rundowns

    @auth
    Scenario: Show CRUD
        When we post to "/shows"
        """
        {"title": "Test", "description": "Test description", "planned_duration": 10.5}
        """
        Then we get response code 201

        When we get "/shows"
        Then we get list with 1 items
        """
        {"_items": [{"title": "Test"}]}
        """

        When we get "/shows/#shows._id#"
        Then we get existing resource
        """
        {"title": "Test", "description": "Test description", "planned_duration": 10.5}
        """

        When we patch "/shows/#shows._id#"
        """
        {"title": "Updated", "planned_duration": 11.1}
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
        [{"title": "Test"}]
        """

        When we post to "/shows/#shows._id#/templates"
        """
        {
            "title": "test template",
            "airtime_time": "06:00",
            "airtime_date": "2050-06-22",
            "title_template": {
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
            "airtime_time": "06:00",
            "created_by": "#CONTEXT_USER_ID#"
        }
        """

        When we patch "/shows/#shows._id#/templates/#templates._id#"
        """
        {"schedule": {"weekday": [5, 6]}, "repeat": false}
        """
        Then we get OK response
        """
        {
            "last_updated_by": "#CONTEXT_USER_ID#"
        }
        """

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
    Scenario: Create rundown using template
        Given "shows"
        """
        [
            {"title": "Test"}
        ]
        """
        And "rundown_templates"
        """
        [
            {
                "title": "Test",
                "show": "#shows._id#",
                "title": "Marker",
                "airtime_time": "06:00",
                "planned_duration": 3600,
                "title_template": {
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
            "template": "#rundown_templates._id#",
            "title": "Marker // 10.06.2022",
            "planned_duration": 3600,
            "airtime_time": "06:00",
            "airtime_date": "2022-06-10",
            "_links": {
                "self": {
                    "href": "rundowns/#rundowns._id#",
                    "title": "Rundowns"
                }
            }
        }
        """

        When we get "/rundowns"
        Then we get list with 1 items
        """
        {"_items": [
            {"title": "Marker // 10.06.2022", "template": "#rundown_templates._id#"}
        ]}
        """
    
    @auth
    Scenario: Validate airtime date when creating/updating template
        Given "shows"
        """
        [
            {"title": "Test"}
        ]
        """

        When we post to "shows/#shows._id#/templates"
        """
        {
            "title": "Test",
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
            "title": "Test",
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
            {"title": "Test"}
        ]
        """
        And "rundown_templates"
        """
        [
            {
                "title": "Scheduled",
                "show": "#shows._id#",
                "airtime_time": "06:00",
                "airtime_date": "2030-01-01",
                "planned_duration": 3600,
                "repeat": true,
                "schedule": {
                    "freq": "DAILY"
                },
                "title_template": {
                    "prefix": "Scheduled",
                    "separator": "//",
                    "date_format": "%d.%m.%Y"
                }
            },
            {
                "title": "Not Scheduled",
                "show": "#shows._id#",
                "airtime_time": "06:00",
                "airtime_date": "2030-01-01",
                "planned_duration": 3600,
                "repeat": false,
                "schedule": {
                    "freq": "DAILY"
                },
                "title_template": {
                    "prefix": "Not Scheduled",
                    "separator": "//",
                    "date_format": "%d.%m.%Y"
                }
            }
        ]
        """

        When we run task "apps.rundowns.tasks.create_scheduled_rundowns"
        And we get "/rundowns"
        Then we get list with 1 items
        """
        {"_items": [
            {"title": "Scheduled // 01.01.2030", "scheduled_on": "2030-01-01T05:00:00+0000"}
        ]}
        """

        When we run task "apps.rundowns.tasks.create_scheduled_rundowns"
        And we get "/rundowns"
        Then we get list with 2 items
        """
        {"_items": [
            {"title": "Scheduled // 01.01.2030", "scheduled_on": "2030-01-01T05:00:00+0000"},
            {"title": "Scheduled // 02.01.2030", "scheduled_on": "2030-01-02T05:00:00+0000"}
        ]}
        """

    @auth
    Scenario: Add items to rundown template
        Given "shows"
        """
        [
            {"title": "Test"}
        ]
        """

        When we post to "/shows/#shows._id#/templates"
        """
        {
            "title": "Scheduled",
            "airtime_time": "06:00",
            "airtime_date": "2030-01-01",
            "planned_duration": 3600
        }
        """

        And we post to "rundown_items"
        """
        {
            "item_type": "text",
            "title": "Test item"
        }
        """
        Then we get new resource

        When we patch "/shows/#shows._id#/templates/#templates._id#"
        """
        {
            "items": [
                {
                    "_id": "#rundown_items._id#",
                    "start_time": "05:00"
                }
            ]
        }
        """
        Then we get ok response

        When we post to "/shows/#shows._id#/rundowns"
        """
        {"template": "#templates._id#", "airtime_date": "2055-06-10"}
        """
        Then we get new resource

        When we get "/rundowns"
        Then we get list with 1 item
        """
        {"_items": [
            {
                "title": "Scheduled",
                "items": [
                    {"start_time": "05:00"}
                ]
            }
        ]}
        """
        When we get "/rundown_items"
        Then we get list with 2 items
        """
        {"_items": [
            {"item_type": "text", "_id": "#rundown_items._id#"},
            {"item_type": "text", "operation": "duplicate", "original_id": "#rundown_items._id#"}
        ]}
        """

    @auth
    Scenario: Rundowns CRUD
        Given "shows"
        """
        [
            {"title": "Test"}
        ]
        """

        When we post to "/rundowns"
        """
        {
            "title": "test",
            "show": "#shows._id#",
            "airtime_time": "06:00",
            "airtime_date": "2030-01-01",
            "planned_duration": 3600
        }
        """

        When we post to "/rundown_items"
        """
        {
            "title": "test",
            "duration": 80,
            "planned_duration": 120,
            "item_type": "test",
            "content": "<p>some text</p>"
        }
        """

        Then we get OK response

        When we get "/rundowns"
        Then we get list with 1 items

        When we patch "/rundowns/#rundowns._id#"
        """
        {"items": [
            {"_id": "#rundown_items._id#"}
        ]}
        """
        Then we get OK response
     