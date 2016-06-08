Feature: Templates

    @auth
    Scenario: Get predefined templates
    Given "desks"
    """
    [
        {"name": "sports"}
    ]
    """
    When we post to "content_templates"
    """
    {"template_name": "kill", "template_type": "kill", "template_desks": ["#desks._id#"], "is_public": true,
     "data": {"anpa_take_key": "TAKEDOWN"}}
    """
    Then we get error 400
    """
    {"_status": "ERR", "_message": "Invalid kill template. schedule, dateline, template_desks, template_stage are not allowed"}
    """
    When we post to "content_templates"
    """
    {"template_name": "kill", "template_type": "kill", "is_public": true, "data": {"anpa_take_key": "TAKEDOWN"}}
    """
    Then we get new resource
    """
    {"_id": "__any_value__", "template_name": "kill", "template_type": "kill", "data": {"anpa_take_key": "TAKEDOWN"}}
    """
    When we get "content_templates/kill"
    Then we get existing resource
    """
    {"_id": "__any_value__", "template_name": "kill", "data": {"anpa_take_key": "TAKEDOWN"}}
    """

    @auth
    Scenario: User can create personal template
        When we post to "content_templates"
        """
        {"template_name": "personal", "template_type": "create", "template_desks": null, "data": {
            "body_footer": "test",
            "sms_message": "foo",
            "flags": {"marked_for_sms": true}
        }}
        """
        Then we get new resource
        """
        {"template_desks": null, "user": "#CONTEXT_USER_ID#", "is_public": false, "data": {"body_footer": "test"}}
        """

    @auth
    Scenario: User can create highlight template
        When we post to "content_templates"
        """
        {"template_name": "default highlight", "template_type": "highlights",
         "data": {"body_html": "{% for item in items %} <h2>{{ item.headline }}</h2> {{ item.body_html }} <p></p> {% endfor %}"}
        }
        """
        Then we get new resource
        """
        {"template_name": "default highlight", "template_type": "highlights"}
        """

    @auth
    Scenario: User can schedule a content creation
        Given "desks"
        """
        [{"name": "sports"}]
        """
        And "stages"
        """
        [{"name": "schedule", "desk": "#desks._id#"}]
        """

        When we post to "content_templates"
        """
        {"template_name": "test", "template_type": "create",
         "data": {"headline": "test", "type": "text", "slugline": "test", "firstcreated": "2015-10-10T10:10:10+0000", "versioncreated": "2015-10-10T10:10:10+0000"},
         "schedule": {"day_of_week": ["MON"], "create_at": "08:15:00", "is_active": true},
         "template_desks": ["#desks._id#"], "template_stage": "#stages._id#"}
        """
        Then we get new resource
        And next run is on monday "08:15:00"

        When we patch latest
        """
        {"schedule": {"day_of_week": ["MON"], "create_at": "09:15:00", "is_active": true}}
        """
        Then next run is on monday "09:15:00"

        When we run create content task
        And we run create content task
        And we get "/archive"
        Then we get list with 1 items
        """
        {"_items": [{
            "headline": "test",
            "firstcreated": "__now__",
            "versioncreated": "__now__",
            "_updated": "__now__",
            "_created": "__now__",
            "_current_version": 1,
            "_etag": "__any_value__"
        }]}
        """
        When we get "/archive/#ITEM_ID#?version=all"
        Then we get list with 1 items

    @auth
    Scenario: User can schedule a content creation with different timezone
        Given "desks"
        """
        [{"name": "sports"}]
        """
        And "stages"
        """
        [{"name": "schedule", "desk": "#desks._id#"}]
        """

        When we post to "content_templates"
        """
        {"template_name": "test", "template_type": "create",
         "data": {"headline": "test", "type": "text", "slugline": "test", "firstcreated": "2015-10-10T10:10:10+0000", "versioncreated": "2015-10-10T10:10:10+0000"},
         "schedule": {"day_of_week": ["MON"], "create_at": "08:15:00", "is_active": true,
         "time_zone": "Australia/Sydney"},
         "template_desks": ["#desks._id#"], "template_stage": "#stages._id#"}
        """
        Then we get new resource
        And next run is on monday "22:15:00"

        When we patch latest
        """
        {"schedule": {"day_of_week": ["MON"], "create_at": "09:15:00", "is_active": true}}
        """
        Then next run is on monday "23:15:00"

        When we run create content task
        And we get "/archive"
        Then we get list with 1 items
        """
        {"_items": [{
            "headline": "test",
            "firstcreated": "__now__",
            "versioncreated": "__now__",
            "_updated": "__now__",
            "_created": "__now__",
            "_current_version": 1,
            "_etag": "__any_value__"
        }]}
        """
        When we get "/archive/#ITEM_ID#?version=all"
        Then we get list with 1 items

    @auth
    Scenario: Apply template to an item
        When we post to "content_templates"
        """
        {
            "template_name": "kill",
            "template_type": "kill",
            "is_public": true,
            "data": {
                "body_html": "<p>Please kill story slugged {{ item.slugline }} ex {{ item.dateline['text'] }} at {{item.versioncreated | format_datetime(date_format='%d %b %Y %H:%S %Z')}}.<\/p>",
                "type": "text",
                "abstract": "This article has been removed",
                "headline": "Kill\/Takedown notice ~~~ Kill\/Takedown notice",
                "urgency": 1, "priority": 1,
                "anpa_take_key": "KILL\/TAKEDOWN"
            }
        }
        """
        Then we get new resource
        When we post to "content_templates_apply"
        """
            {
                "template_name": "kill",
                "item": {
                    "headline": "Test", "_id": "123",
                    "body_html": "test", "slugline": "testing",
                    "abstract": "abstract",
                    "urgency": 5, "priority": 6,
                    "dateline": {
                        "text": "Prague, 9 May (SAP)"
                    },
                    "versioncreated": "2015-01-01T22:54:53+0000"
                }
            }
        """
        Then we get updated response
        """
        {
          "_id": "123",
          "headline": "Kill\/Takedown notice ~~~ Kill\/Takedown notice",
          "body_html": "<p>Please kill story slugged testing ex Prague, 9 May (SAP) at 01 Jan 2015 23:53 CET.<\/p>",
          "anpa_take_key": "KILL\/TAKEDOWN",
          "slugline": "testing",
          "urgency": 1, "priority": 1,
          "abstract": "This article has been removed",
          "dateline": {
            "text": "Prague, 9 May (SAP)"
          },
          "versioncreated": "2015-01-01T22:54:53+0000"

        }
        """

    @auth
    Scenario: For kill Template Dateline, Schedule and Desk settings should be null.
    Given "desks"
    """
    [
        {"name": "sports"}
    ]
    """
    When we post to "content_templates"
    """
    {
     "template_name": "test", "template_type": "create",
     "template_desks": ["#desks._id#"], "template_stage": "#desks.incoming_stage#",
     "schedule": {"create_at": "08:00:00", "day_of_week": ["MON", "TUE"]},
     "data": {
        "anpa_take_key": "TAKEDOWN",
        "urgency": 1,
        "priority": 1,
        "headline": "headline",
        "dateline": {"text": "Test"}
     }
    }
    """
    Then we get new resource
    """
    {"_id": "__any_value__",
     "template_name": "test", "template_type": "create",
     "template_desks": ["#desks._id#"], "template_stage": "#desks.incoming_stage#",
     "schedule": {"create_at": "08:00:00", "day_of_week": ["MON", "TUE"]},
     "data": {
        "anpa_take_key": "TAKEDOWN", "urgency": 1, "priority": 1, "headline": "headline", "dateline": {"text": "Test"}
     }
    }
    """
    When we patch latest
    """
    {"template_type": "kill", "template_name": "testing"}
    """
    Then we get updated response
    """
    {"_id": "__any_value__",
     "template_name": "testing", "template_type": "kill",
     "template_desks": null, "template_stage": null,
     "schedule": null,
     "data": {"anpa_take_key": "TAKEDOWN", "urgency": 1, "priority": 1, "headline": "headline", "dateline": null}
    }
    """


    @auth
    Scenario: Validate unique name on personal template
        When we post to "content_templates"
        """
        {"template_name": "personal", "template_type": "create", "template_desks": null, "data": {"body_footer": "test"}}
        """
        Then we get new resource
        """
        {"template_desks": null, "user": "#CONTEXT_USER_ID#", "is_public": false, "data": {"body_footer": "test"}}
        """

        When we post to "content_templates"
        """
        {"template_name": "personal", "template_type": "create", "template_desks": null, "data": {"body_footer": "test"}}
        """
        Then we get error 400
        """
        {"_error": {"code": 400, "message": "Insertion failure: 1 document(s) contain(s) error(s)"},
         "_issues": {"template_name": "Template Name is not unique"},
         "_status": "ERR"
        }
        """
        When we post to "content_templates"
        """
        {"template_name": "PERSONAL", "template_type": "create", "template_desks": null, "data": {"body_footer": "test"}}
        """
        Then we get error 400
        """
        {"_error": {"code": 400, "message": "Insertion failure: 1 document(s) contain(s) error(s)"},
         "_issues": {"template_name": "Template Name is not unique"},
         "_status": "ERR"
        }
        """


    @auth
    Scenario: Validate unique name on desk template
        Given "desks"
        """
        [
            {"name": "sports"}
        ]
        """
        When we post to "content_templates"
        """
        {
         "template_name": "desk", "template_type": "create", "data": {"body_footer": "test"},
         "template_desks": ["#desks._id#"], "template_stage": "#desks.incoming_stage#", "is_public": true
         }
        """
        Then we get new resource
        """
        {
         "template_name": "desk", "template_type": "create", "data": {"body_footer": "test"},
         "template_desks": ["#desks._id#"], "template_stage": "#desks.incoming_stage#", "is_public": true
         }
        """

        When we post to "content_templates"
        """
        {
         "template_name": "desk", "template_type": "create", "data": {"body_footer": "test"},
         "template_desks": ["#desks._id#"], "template_stage": "#desks.incoming_stage#", "is_public": true
         }
        """
        Then we get error 400
        """
        {"_error": {"code": 400, "message": "Insertion failure: 1 document(s) contain(s) error(s)"},
         "_issues": {"is_public": "Template Name is not unique", "template_name": "Template Name is not unique"},
         "_status": "ERR"
        }
        """
        When we post to "content_templates"
        """
        {
         "template_name": "Desk", "template_type": "create", "data": {"body_footer": "test"},
         "template_desks": ["#desks._id#"], "template_stage": "#desks.incoming_stage#", "is_public": true
         }
        """
        Then we get error 400
        """
        {"_error": {"code": 400, "message": "Insertion failure: 1 document(s) contain(s) error(s)"},
         "_issues": {"is_public": "Template Name is not unique", "template_name": "Template Name is not unique"},
         "_status": "ERR"
        }
        """

    @auth
    Scenario: Add personal and desk templates with the same name and then try to change the non public to public
        Given "desks"
        """
        [
            {"name": "sports"}
        ]
        """
        When we post to "content_templates"
        """
        {
         "template_name": "template", "template_type": "create", "data": {"body_footer": "test"},
         "template_desks": ["#desks._id#"], "template_stage": "#desks.incoming_stage#", "is_public": true
         }
        """
        Then we get new resource
        """
        {
         "template_name": "template", "template_type": "create", "data": {"body_footer": "test"},
         "template_desks": ["#desks._id#"], "template_stage": "#desks.incoming_stage#", "is_public": true
         }
        """

        When we post to "content_templates"
        """
        {"template_name": "template", "template_type": "create", "template_desks": null, "data": {"body_footer": "test"}}
        """
        Then we get new resource
        """
        {"template_desks": null, "user": "#CONTEXT_USER_ID#", "is_public": false, "data": {"body_footer": "test"}}
        """

        When we patch "content_templates/#content_templates._id#"
        """
        {"is_public": true}
        """
        Then we get error 400
        """
        {"_issues": {"is_public": "Template Name is not unique"},
         "_status": "ERR"
        }
        """
        When we patch "content_templates/#content_templates._id#"
        """
        {"template_name": "TEMPLATE"}
        """
        Then we get OK response
        When we patch "content_templates/#content_templates._id#"
        """
        {"is_public": true}
        """
        Then we get error 400
        """
        {"_issues": {"is_public": "Template Name is not unique"},
         "_status": "ERR"
        }
        """

    @auth
    Scenario: Add create type templates assigned to multiple desks
        Given "desks"
        """
        [
            {"_id": "5754869b95cc64157018996c", "name": "sports"},
            {"_id": "5754866c95cc641570189967", "name": "politics"}
        ]
        """
        When we post to "content_templates"
        """
        {
         "template_name": "template", "template_type": "create", "data": {"body_footer": "test"},
         "template_desks": ["5754869b95cc64157018996c", "5754866c95cc641570189967"], "is_public": true
         }
        """
        Then we get new resource
        """
        {
         "template_name": "template", "template_type": "create", "data": {"body_footer": "test"},
         "template_desks": ["5754869b95cc64157018996c", "5754866c95cc641570189967"], "is_public": true
         }
        """

    @auth
    Scenario: Can not assign highlight template to multiple desks
        Given "desks"
        """
        [
            {"_id": "5754869b95cc64157018996c", "name": "sports"},
            {"_id": "5754866c95cc641570189967", "name": "politics"}
        ]
        """
        When we post to "content_templates"
        """
        {
         "template_name": "template", "template_type": "highlights", "data": {"body_footer": "test"},
         "template_desks": ["5754869b95cc64157018996c", "5754866c95cc641570189967"], "is_public": true
         }
        """
        Then we get error 400
        """
        {"_message": "Templates that are not create type can only be assigned to one desk!",
         "_status": "ERR"
        }
        """
