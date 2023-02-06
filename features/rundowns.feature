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

    @auth
    Scenario: Templates CRUD
        Given "shows"
        """
        [{"title": "Test", "shortcode": "TST"}]
        """

        When we post to "/shows/#shows._id#/templates"
        """
        {
            "title": "test template",
            "airtime_time": "06:00",
            "airtime_date": "2030-06-22",
            "title_template": {
                "prefix": "Marker",
                "separator": "//",
                "date_format": "dd.mm.yy"
            },
            "repeat": true,
            "schedule": {
                "freq": "DAILY",
                "interval": 1,
                "by_day": [0]
            },
            "autocreate_before_seconds": 3600,
            "items": [
                {
                    "planned_duration": 600,
                    "item_type": "PRLG",
                    "title": "Item title"
                },
                {
                    "planned_duration": 400,
                    "item_type": "AACC",
                    "title": "Item title 2"
                },
                {
                    "planned_duration": 200,
                    "item_type": "another",
                    "title": "Foo"
                }
            ]
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
            "airtime_date": "2030-06-22",
            "airtime_time": "06:00",
            "created_by": "#CONTEXT_USER_ID#",
            "scheduled_on": "2030-06-24T04:00:00+0000",
            "autocreate_on": "2030-06-24T03:00:00+0000",
            "items": [
                {
                    "technical_title": "PRLG-TST-ITEM-TITLE"
                },
                {
                    "technical_title": "AACC-TST-ITEM-TITLE-2"
                },
                {
                    "technical_title": "FOO"
                }
            ]
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
                },
                "items": [
                    {
                        "duration": 600,
                        "item_type": "Test",
                        "title": "Item title"
                    },
                    {
                        "duration": 400,
                        "item_type": "Test2",
                        "title": "Item title 2"
                    }
                ]
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
            "airtime_date": "2022-06-10",
            "items": [
                {"_id": "__objectid__"},
                {"_id": "__objectid__"}
            ]
        }
        """

        When we get "/rundowns"
        Then we get list with 1 items
        """
        {"_items": [
            {"title": "Marker // 10.06.2022", "template": "#rundown_templates._id#", "items": [
                {"_id": "__objectid__"},
                {"_id": "__objectid__"}
            ]}
        ]}
        """

        When we get "/rundown_items"
        Then we get list with 2 items

        When we patch "/rundowns/#rundowns._id#"
        """
        {"_lock_action": "lock"}
        """
        Then we get OK response
        """
        {
            "items": [
                {"_id": "__objectid__"},
                {"_id": "__objectid__"}
            ]
        }
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
            "airtime_time": "08:00",
            "items": [
                {"_id": "__objectid__"},
                {"_id": "__objectid__"}
            ]
        }
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
                },
                "autocreate_before_seconds": 1
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
                },
                "autocreate_before_seconds": 86400,
                "items": [
                    {
                        "duration": 600,
                        "item_type": "Test",
                        "title": "Item title"
                    },
                    {
                        "duration": 400,
                        "item_type": "Test2",
                        "title": "Item title 2"
                    }
                ]
            }
        ]
        """

        When we run task "apps.rundowns.tasks.create_scheduled_rundowns"
        And we get "/rundowns"
        Then we get list with 1 items
        """
        {"_items": [
            {"title": "Scheduled // 06:00", "scheduled_on": "__future__"}
        ]}
        """

        When we get "/rundown_items"
        Then we get list with 2 items
        """
        {
            "_items": [
                {"technical_title": "ITEM TITLE"},
                {"technical_title": "ITEM TITLE 2"}
            ]
        }
        """

        When we run task "apps.rundowns.tasks.create_scheduled_rundowns"
        And we get "/rundowns"
        Then we get list with 1 items

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
            {"title": "Test", "shortcode": "SHO"}
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
            "title": "test title",
            "duration": 80,
            "planned_duration": 120,
            "item_type": "PRLG",
            "content": "<p>some text</p>",
            "subitems": [
                {"qcode": "wall"},
                {"qcode": "video"}
            ],
            "rundown": "#rundowns._id#",
            "camera": ["k1", "k2"]
        }
        """
        Then we get OK response
        """
        {"_links": {"self": {"title": "rundown_items"}}, "technical_title": "PRLG-SHO-TEST-TITLE-K1-K2"}
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
        {"duration": 200, "planned_duration": 300, "item_type": "FOO"}
        """
        Then we get OK response
        """
        {"technical_title": "TEST TITLE"}
        """

        When we get "/rundowns/#rundowns._id#"
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
        {"_lock_action": "lock"}
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
        When we patch "/rundowns/#rundowns._id#"
        """
        {"_lock_action": "unlock"}
        """
        Then we get error 412
        When we patch "/rundowns/#rundowns._id#"
        """
        {"_lock_action": "lock"}
        """
        Then we get error 412

        When we patch "/rundowns/#rundowns._id#"
        """
        {"_lock_action": "force-lock"}
        """
        Then we get ok response
        """
        {"_lock": true}
        """

        When the lock expires "/rundowns/#rundowns._id#"

        When we patch "/rundowns/#rundowns._id#"
        """
        {"title": "bar"}
        """
        Then we get ok response

        When we patch "/rundowns/#rundowns._id#"
        """
        {"_lock_action": "lock"}
        """
        Then we get ok response

        When we patch "/rundowns/#rundowns._id#"
        """
        {"_lock_action": "unlock"}
        """
        Then we get ok response
        """
        {"_lock_user": null, "_lock_time": null, "_lock_session": null, "_lock": false}
        """

        When we login as user "foo2" with password "bar" and user type "administrator"

        And we patch "/rundowns/#rundowns._id#"
        """
        {"title": "bar"}
        """
        Then we get ok response

        When the lock expires "/rundowns/#rundowns._id#"

        When we patch "/rundowns/#rundowns._id#"
        """
        {"title": "bar"}
        """
        Then we get ok response

        When we patch "/rundowns/#rundowns._id#"
        """
        {"_lock_action": "lock"}
        """
        Then we get ok response

        When we patch "/rundowns/#rundowns._id#"
        """
        {"_lock_action": "unlock"}
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
        Given "vocabularies"
        """
        [
            {"_id": "rundown_subitem_types", "items": [
                {"name": "PRLG", "qcode": "PRLG", "is_active": true},
                {"name": "WALL", "qcode": "WALL", "is_active": true},
                {"name": "GRAF", "qcode": "GRAF", "is_active": true}
            ]},
            {"_id": "rundown_item_types", "items": [
                {"name": "PRLG Name", "qcode": "PRLG"}
            ]}
        ]
        """

        When we get "/rundown_export"
        Then we get list with 3 items
        """
        {"_items": [
            {"name": "Prompter PDF", "_id": "prompter-pdf"},
            {"name": "Technical CSV", "_id": "table-csv"},
            {"name": "Technical PDF", "_id": "table-pdf"}
        ]}
        """

        Given "shows"
        """
        [
            {"title": "Test", "shortcode": "MRK"}
        ]
        """

        And "rundowns"
        """
        [
            {
                "show": "#shows._id#",
                "title": "Rundown Title // 10.10.2022",
                "airtime_time": "06:00",
                "airtime_date": "2030-01-01",
                "planned_duration": 3600
            }
        ]
        """

        And "rundown_items"
        """
        [
            {
                "title": "sample",
                "duration": 80,
                "planned_duration": 120,
                "item_type": "PRLG",
                "content": "<p>foo</p><p>bar</p>",
                "camera": ["K1", "K2"],
                "additional_notes": "Some extra notes",
                "rundown": "#rundowns._id#",
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
                                    },
                                    {
                                        "key": "6lrsd",
                                        "type": "unstyled",
                                        "depth": 0,
                                        "text": "Šta nas čeka od jeseni? Najave poskupljenja osnovnih životnih namirnica, zabrinutost kako i čime ćemo da se grejemo sledeće zime, strepnja od poskupljenja, samo su neki od strahova s kojima dočekujemo leto.",
                                        "inlineStyleRanges": [],
                                        "entityRanges": [],
                                        "data": {}
                                    }
                                ]
                            }
                        ]
                    }
                },
                "subitems": [
                    {
                        "qcode": "WALL",
                        "technical_info": "wall info",
                        "content": "some content"
                    },
                    {
                        "qcode": "PRLG",
                        "technical_info": "prlg info, some other info",
                        "content": "another content"
                    }
                ]
            }
        ]
        """

        When we patch "rundowns/#rundowns._id#"
        """
        {
            "items": [
                {"_id": "#rundown_items._id#"},
                {"_id": "#rundown_items._id#"}
            ]
        }

        """
        Then we get OK response

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
        And we get "Content-Disposition" header with "attachment; filename="Prompter-Rundown_Title_10.10.2022.pdf"" type
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
        And we get "Content-Disposition" header with "attachment; filename="Technical-Rundown_Title_10.10.2022.csv"" type
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
        And we get "Content-Disposition" header with "attachment; filename="Technical-Rundown_Title_10.10.2022.pdf"" type
        And we get "Content-Type" header with "application/pdf" type

    @auth
    Scenario: Search rundown by item contents
        Given "shows"
        """
        [
            {"title": "Test", "shortcode": "MRK"}
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
                "planned_duration": 3600
            }
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
                "subitems": [
                    {"qcode": "wall"},
                    {"qcode": "video"}
                ],
                "content": "<p>searchable content</p>",
                "rundown": "#rundowns._id#"
            }
        ]
        """

        When we patch "/rundowns/#rundowns._id#"
        """
        {
            "items": [
                {"_id": "#rundown_items._id#"}
            ]
        }
        """

        When we get "/rundowns?q=searchable"
        Then we get list with 1 items
        """
        {
            "_items": [
                {
                    "title": "Rundown Title",
                    "matching_items": [
                        {"title": "sample"}
                    ]
                }
            ]
        }
        """

        When we get "/rundowns?q=title"
        Then we get list with 1 items
        """
        {
            "_items": [
                {
                    "title": "Rundown Title",
                    "matching_items": [
                    ]
                }
            ]
        }
        """

        When we get "/rundowns?q=missing"
        Then we get list with 0 items

        When we post to "/rundown_items"
        """
        {
            "title": "missing",
            "duration": 80,
            "planned_duration": 120,
            "item_type": "test",
            "subitems": [
                {"qcode": "wall"},
                {"qcode": "video"}
            ],
            "content": "<p>content</p>",
            "rundown": "#rundowns._id#"
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

    @auth
    @notification
    Scenario: Rundown comments
        Given "shows"
        """
        [
            {"title": "Test", "shortcode": "MRK"}
        ]
        """

        And "rundowns"
        """
        [
            {
                "show": "#shows._id#",
                "title": "Rundown Title",
                "planned_duration": 3600
            }
        ]
        """

        And "rundown_items"
        """
        [
            {"title": "Test", "rundown": "#rundowns._id#"}
        ]
        """

        When we post to "/rundown_comments"
        """
        {"text": "test @test_user", "item": "#rundown_items._id#"}
        """
        Then we get ok response

        When we get "/rundown_comments?where={"item":"#rundown_items._id#"}"
        Then we get list with 1 items
        """
        {"_items": [
            {"text": "test @test_user", "user": "#CONTEXT_USER_ID#"}
        ]}
        """

        When we get "/activity"
        Then we get list with 1+ items
        """
        {"_items": [
            {
                "name": "rundown-item-comment",
                "message": "You were mentioned in \"Test\" (\"Rundown Title\") comment by test_user.",
                "data": {
                    "message": "test @test_user",
                    "rundownId": "#rundowns._id#",
                    "rundownItemId": "#rundown_items._id#",
                    "extension": "broadcasting"
                }
            }
        ]}
        """
