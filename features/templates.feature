@wip
Feature: Templates

    @auth
    Scenario: Get predifined templates
    Given "desks"
    """
    [
        {"name": "sports"}
    ]
    """
    When we post to "content_templates"
    """
    {"template_name": "kill", "template_type": "kill", "template_desk": "#desks._id#",
     "data": {"anpa_take_key": "TAKEDOWN"}}
    """
    Then we get error 400
    """
    {"_status": "ERR", "_message": "Invalid kill template. schedule, dateline, template_desk, template_stage are not allowed"}
    """
    When we post to "content_templates"
    """
    {"template_name": "kill", "template_type": "kill", "data": {"anpa_take_key": "TAKEDOWN"}}
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
        {"template_name": "personal", "template_type": "create", "template_desk": null}
        """
        Then we get new resource
        """
        {"template_desk": null, "user": "#CONTEXT_USER_ID#", "is_public": false}
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
         "schedule": {"day_of_week": ["MON"], "create_at": "0815", "is_active": true},
         "template_desk": "#desks._id#", "template_stage": "#stages._id#"}
        """
        Then we get new resource
        And next run is on monday "0815"

        When we patch latest
        """
        {"schedule": {"day_of_week": ["MON"], "create_at": "0915", "is_active": true}}
        """
        Then next run is on monday "0915"

        When we run create content task
        And we run create content task
        And we get "/archive"
        Then we get list with 1 items
        """
        {"_items": [{"headline": "test", "firstcreated": "__now__", "versioncreated": "__now__"}]}
        """

    @auth
    Scenario: Apply template to an item
        When we post to "content_templates"
        """
        {
            "template_name": "kill",
            "template_type": "kill",
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

    @wip
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
     "template_desk": "#desks._id#", "template_stage": "#desks.incoming_stage#",
     "schedule": {"create_at": "08:00", "day_of_week": ["MON", "TUE"]},
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
     "template_desk": "#desks._id#", "template_stage": "#desks.incoming_stage#",
     "schedule": {"create_at": "08:00", "day_of_week": ["MON", "TUE"]},
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
     "template_desk": null, "template_stage": null,
     "schedule": null,
     "data": {"anpa_take_key": "TAKEDOWN", "urgency": 1, "priority": 1, "headline": "headline", "dateline": null}
    }
    """