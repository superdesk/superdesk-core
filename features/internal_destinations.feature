Feature: Internal Destinations

    @auth
    Scenario: Create items for destinations on publish
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        When we post to "archive" with success
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "Take-1 headline",
            "abstract": "Take-1 abstract",
            "task": {
                "user": "#CONTEXT_USER_ID#",
                "desk": "#desks._id#",
                "stage": "#desks.working_stage#"
            },
            "body_html": "Body $10",
            "state": "submitted",
            "slugline": "Take-1 slugline",
            "urgency": "4",
            "pubstatus": "usable",
            "subject":[{"qcode": "17004000", "name": "Statistics"}],
            "anpa_category": [{"qcode": "A", "name": "Sport"}],
            "anpa_take_key": "Take",
            "publish_schedule": "2099-05-19T10:15:00",
            "schedule_settings": {
                "time_zone": "Europe/London",
                "utc_publish_schedule": "2099-05-19T09:15:00+0000"
            }
        }]
        """

        When we post to "desks"
        """
        {"name": "Features"}
        """

        Given "internal_destinations"
        """
        [{"name": "copy", "is_active": true, "desk": "#desks._id#", "macro": "usd_to_cad"}]
        """

        When we publish "#archive._id#" with "publish" type and "published" state
        Then we get OK response

        When we get "/archive"
        Then we get list with 1 items
        """
        {"_items": [{
            "state": "routed",
            "family_id": "#archive._id#",
            "task": {"desk": "#desks._id#"},
            "body_html": "Body $10 (CAD 20)",
            "publish_schedule": "2099-05-19T10:15:00+0000",
            "schedule_settings": {
                "time_zone": "Europe/London",
                "utc_publish_schedule": "2099-05-19T09:15:00+0000"
            }
        }]}
        """
