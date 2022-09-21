Feature: Rundowns

    @auth
    Scenario: Show CRUD
        When we post to "/shows"
        """
        {"title": "Test", "description": "Test description", "planned_duration": 10.5}
        """
        Then we get response code 201
        """
        {"_links": {"self": {"title": "shows"}}}
        """

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

    @wip
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
                "by_month": [1],
                "by_month_day": [1, -1],
                "by_day": [1]
            }
        }
        """
        Then we get new resource
        """
        {
            "_links": {
                "self": {
                    "href": "/shows/#shows._id#/templates/#templates._id#",
                    "title": "rundown_templates"
                }
            },
            "airtime_date": "2050-06-22",
            "airtime_time": "06:00",
            "created_by": "#CONTEXT_USER_ID#"
        }
        """

        When we patch "/shows/#shows._id#/templates/#templates._id#"
        """
        {"schedule": {"by_day": [5, 6]}, "repeat": false}
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
        {"_items": [{"schedule": {"by_day": [5, 6]}, "repeat": false}]}
        """

        When we delete "/shows/#shows._id#/templates/#templates._id#"
        Then we get OK response

        When we get "/shows/#shows._id#/templates"
        Then we get list with 0 items

    @auth
    Scenario: Create rundown from template
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

        When we post to "/rundowns"
        """
        {"show": "#shows._id#", "template": "#rundown_templates._id#", "airtime_date": "2022-06-10"}
        """
        Then we get new resource
        """
        {
            "show": "#shows._id#",
            "template": "#rundown_templates._id#",
            "title": "Marker // 10.06.2022",
            "planned_duration": 3600,
            "airtime_time": "06:00",
            "airtime_date": "2022-06-10"
        }
        """

        When we get "/rundowns"
        Then we get list with 1 items
        """
        {"_items": [
            {"title": "Marker // 10.06.2022", "template": "#rundown_templates._id#"}
        ]}
        """
        
        When we post to "/rundowns"
        """
        {
            "show": "#shows._id#",
            "template": "#rundown_templates._id#",
            "airtime_date": "2022-06-10",
            "airtime_time": "08:00",
            "title": "Custom"
        }
        """
        Then we get new resource
        """
        {
            "title": "Custom",
            "airtime_time": "08:00"
        }
        """

    @wip
    @auth
    Scenario: Reset scheduled_on when updating schedule settings
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
            "repeat": true,
            "schedule": {
                "freq": "DAILY"
            }
        }
        """
        Then we get ok response

        When we run task "apps.rundowns.tasks.create_scheduled_rundowns"
        And we get "shows/#shows._id#/templates/#templates._id#"
        Then we get existing resource
        """
        {"scheduled_on": "__future__"}
        """

        When we patch "shows/#shows._id#/templates/#templates._id#"
        """
        {
            "title": "Test",
            "airtime_time": "06:00",
            "repeat": true,
            "schedule": {
                "freq": "DAILY",
                "by_day": [3]
            }
        }
        """
        Then we get ok response
        """
        {"scheduled_on": null}
        """

    @wip
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
                "title": "Scheduled one",
                "show": "#shows._id#",
                "airtime_time": "18:00",
                "planned_duration": 3600,
                "repeat": true,
                "schedule": {
                    "freq": "DAILY"
                },
                "title_template": {
                    "prefix": "Scheduled",
                    "separator": "//",
                    "date_format": "%H:%M"
                }
            },
            {
                "title": "Scheduled two",
                "show": "#shows._id#",
                "airtime_time": "06:00",
                "planned_duration": 3600,
                "repeat": true,
                "schedule": {
                    "freq": "DAILY"
                },
                "title_template": {
                    "prefix": "Scheduled",
                    "separator": "//",
                    "date_format": "%H:%M"
                }
            }
        ]
        """

        When we run task "apps.rundowns.tasks.create_scheduled_rundowns"
        And we get "/rundowns"
        Then we get list with 2 items
        """
        {"_items": [
            {"title": "Scheduled // 18:00", "scheduled_on": "__future__"},
            {"title": "Scheduled // 06:00", "scheduled_on": "__future__"}
        ]}
        """

        When we run task "apps.rundowns.tasks.create_scheduled_rundowns"
        And we get "/rundowns"
        Then we get list with 2 items

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
            "planned_duration": 3600
        }
        """

        When we patch "/shows/#shows._id#/templates/#templates._id#"
        """
        {
            "items": [
                {
                    "item_type": "text",
                    "title": "Test item"
                }
            ]
        }
        """
        Then we get ok response

        When we post to "/rundowns"
        """
        {"show": "#shows._id#", "template": "#templates._id#"}
        """
        Then we get new resource

        When we get "/rundowns"
        Then we get list with 1 item
        """
        {"_items": [
            {
                "title": "Scheduled",
                "items": [
                    {"_id": "__objectid__"}
                ]
            }
        ]}
        """
        When we get "/rundown_items"
        Then we get list with 1 items
        """
        {"_items": [
            {"item_type": "text", "title": "Test item"}
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
            "show": "#shows._id#",
            "airtime_time": "06:00",
            "airtime_date": "2030-01-01",
            "planned_duration": 3600
        }
        """
        Then we get ok response
        """
        {"_links": {"self": {"title": "rundowns"}}}
        """

        When we post to "/rundown_items"
        """
        {
            "title": "test",
            "duration": 80,
            "planned_duration": 120,
            "item_type": "test",
            "content": "<p>some text</p>",
            "subitems": ["wall", "video"]
        }
        """
        Then we get OK response
        """
        {"_links": {"self": {"title": "rundown_items"}}}
        """

        When we get "/rundowns"
        Then we get list with 1 items
        """
        {"_items": [
            {
                "title": "Test",
                "show": "#shows._id#",
                "airtime_time": "06:00",
                "airtime_date": "2030-01-01",
                "planned_duration": 3600
            }
        ]}
        """

        When we patch "/rundowns/#rundowns._id#"
        """
        {"items": [
            {"_id": "#rundown_items._id#"},
            {"_id": "#rundown_items._id#"}
        ]}
        """
        Then we get OK response

        When we get "/rundowns/#rundowns._id#"
        Then we get existing resource
        """
        {"duration": 160, "planned_duration": 3600}
        """

        When we patch "/rundown_items/#rundown_items._id#"
        """
        {"duration": 200, "planned_duration": 300}
        """
        And we get "/rundowns/#rundowns._id#"
        Then we get existing resource
        """
        {"duration": 400, "planned_duration": 3600}
        """

        When we delete "/rundowns/#rundowns._id#"
        Then we get OK response

        When we delete "/rundown_items/#rundown_items._id#"
        Then we get OK response


    @auth
    Scenario: Create rundown for today
        Given "shows"
        """
        [
            {"title": "Test"}
        ]
        """

        When we post to "/rundowns"
        """
        {
            "show": "#shows._id#",
            "airtime_time": "06:00",
            "title": "Todays rundown"
        }
        """

        Then we get ok response
        """
        {
            "title": "Todays rundown",
            "airtime_time": "06:00",
            "airtime_date": "__today__"
        }
        """

    @auth
    Scenario: Locking
        Given "shows"
        """
        [
            {"title": "Test"}
        ]
        """

        When we post to "/rundowns"
        """
        {
            "show": "#shows._id#",
            "airtime_time": "06:00"
        }
        """
        Then we get ok response

        When we patch "/rundowns/#rundowns._id#"
        """
        {"_lock": true}
        """
        Then we get ok response
        """
        {
            "_lock": true,
            "_lock_user": "#CONTEXT_USER_ID#",
            "_lock_time": "__now__"
        }
        """
        When we patch "/rundowns/#rundowns._id#"
        """
        {"title": "foo"}
        """
        Then we get ok response

        When we login as user "foo" with password "bar" and user type "administrator"
 
        And we patch "/rundowns/#rundowns._id#"
        """
        {"title": "bar"}
        """
        Then we get error 412
        """
        {"_error": {"message": "Resource is locked."}}
        """

        When the lock expires "/rundowns/#rundowns._id#"

        When we patch "/rundowns/#rundowns._id#"
        """
        {"title": "bar"}
        """
        Then we get ok response

        When we patch "/rundowns/#rundowns._id#"
        """
        {"_lock": true}
        """
        Then we get ok response

        When we patch "/rundowns/#rundowns._id#"
        """
        {"_lock": false}
        """
        Then we get ok response
        """
        {"_lock_user": null, "_lock_time": null, "_lock_session": null}
        """

        When we login as user "foo2" with password "bar" and user type "administrator"
 
        And we patch "/rundowns/#rundowns._id#"
        """
        {"title": "bar"}
        """
        Then we get ok response
    
    @auth
    Scenario: Export
        When we get "/rundown_export"
        Then we get list with 3 items
        """
        {"_items": [
            {"name": "Prompter PDF", "_id": "prompter-pdf"},
            {"name": "Realizer CSV", "_id": "table-csv"},
            {"name": "Realizer PDF", "_id": "table-pdf"}
        ]}
        """

        Given "shows"
        """
        [
            {"title": "Test", "shortcode": "MRK"}
        ]
        """

        And "rundown_items"
        """
        [
            {
                "title": "sample",
                "duration": 80,
                "planned_duration": 120,
                "item_type": "test",
                "subitems": ["wall", "video"],
                "content": "<p>foo</p><p>bar</p>",
                "fields_meta": {
                    "content": {
                        "draftjsState": [
                            {
                                "blocks": [
                                    {
                                        "key": "41kgq",
                                        "text": "try some really long text so we will see how that wraps and if that will actually add some space after",
                                        "type": "unstyled",
                                        "depth": 0,
                                        "inlineStyleRanges": [],
                                        "entityRanges": [],
                                        "data": {
                                        "MULTIPLE_HIGHLIGHTS": {}
                                        }
                                    },
                                    {
                                        "key": "42kgq",
                                        "text": "try some really long text so we will see how that wraps and if that will actually add some space after",
                                        "type": "unstyled",
                                        "depth": 0,
                                        "inlineStyleRanges": [],
                                        "entityRanges": [],
                                        "data": {
                                        "MULTIPLE_HIGHLIGHTS": {}
                                        }
                                    },
                                    {
                                        "key": "jr6v",
                                        "text": "list1",
                                        "type": "unordered-list-item",
                                        "depth": 0,
                                        "inlineStyleRanges": [],
                                        "entityRanges": [],
                                        "data": {}
                                    },
                                    {
                                        "key": "4grar",
                                        "text": "list2",
                                        "type": "unordered-list-item",
                                        "depth": 0,
                                        "inlineStyleRanges": [],
                                        "entityRanges": [],
                                        "data": {}
                                    },
                                    {
                                        "key": "aiq9u",
                                        "text": "",
                                        "type": "unstyled",
                                        "depth": 0,
                                        "inlineStyleRanges": [],
                                        "entityRanges": [],
                                        "data": {}
                                    },
                                    {
                                        "key": "5lrsd",
                                        "text": "baz",
                                        "type": "ordered-list-item",
                                        "depth": 0,
                                        "inlineStyleRanges": [],
                                        "entityRanges": [],
                                        "data": {}
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        ]
        """

        And "rundowns"
        """
        [
            {
                "show": "#shows._id#",
                "title": "Rundown Title",
                "airtime_time": "06:00",
                "airtime_date": "2030-01-01",
                "planned_duration": 3600,
                "items": [
                    {"_id": "#rundown_items._id#"},
                    {"_id": "#rundown_items._id#"}
                ]
            }
        ]
        """

        When we post to "rundown_export"
        """
        {"format": "prompter-pdf", "rundown": "#rundowns._id#"}
        """
        Then we get response code 201
        """
        {"href": "__any_value__"}
        """

        When we get "#rundown_export.href#"
        Then we get response code 200
        And we get "Content-Disposition" header with "attachment; filename="Prompter-Rundown Title.pdf"" type
        And we get "Content-Type" header with "application/pdf" type

        When we post to "rundown_export"
        """
        {"format": "table-csv", "rundown": "#rundowns._id#"}
        """
        Then we get response code 201
        """
        {"href": "__any_value__"}
        """

        When we get "#rundown_export.href#"
        Then we get response code 200
        And we get "Content-Disposition" header with "attachment; filename="Realizer-Rundown Title.csv"" type
        And we get "Content-Type" header with "text/csv; charset=utf-8" type

        When we post to "rundown_export"
        """
        {"format": "table-pdf", "rundown": "#rundowns._id#"}
        """
        Then we get response code 201
        """
        {"href": "__any_value__"}
        """

        When we get "#rundown_export.href#"
        Then we get response code 200
        And we get "Content-Disposition" header with "attachment; filename="Realizer-Rundown Title.pdf"" type
        And we get "Content-Type" header with "application/pdf" type

    @auth
    Scenario: Search rundown by item contents
        Given "shows"
        """
        [
            {"title": "Test", "shortcode": "MRK"}
        ]
        """

        And "rundown_items"
        """
        [
            {
                "title": "sample",
                "duration": 80,
                "planned_duration": 120,
                "item_type": "test",
                "subitems": ["wall", "video"],
                "content": "<p>searchable content</p>"
            }
        ]
        """

        And "rundowns"
        """
        [
            {
                "show": "#shows._id#",
                "title": "Rundown Title",
                "airtime_time": "06:00",
                "airtime_date": "2030-01-01",
                "planned_duration": 3600,
                "items": [
                    {"_id": "#rundown_items._id#"}
                ]
            }
        ]
        """

        When we get "/rundowns?q=searchable"
        Then we get list with 1 items

        When we get "/rundowns?q=title"
        Then we get list with 1 items

        When we get "/rundowns?q=missing"
        Then we get list with 0 items

        When we post to "/rundown_items"
        """
        {
            "title": "missing",
            "duration": 80,
            "planned_duration": 120,
            "item_type": "test",
            "subitems": ["wall", "video"],
            "content": "<p>content</p>"
        }
        """
        Then we get ok response

        When we patch "/rundowns/#rundowns._id#"
        """
        {"items": [
            {"_id": "#rundown_items._id#"}
        ], "title": "wat?"}
        """
        Then we get ok response

        When we get "/rundowns?q=missing"
        Then we get list with 1 items

        When we patch "/rundown_items/#rundown_items._id#"
        """
        {"content": "<p>another</p>", "title": "another"}
        """
        And we get "/rundowns?q=missing"
        Then we get list with 0 items
