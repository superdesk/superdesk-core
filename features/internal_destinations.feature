Feature: Internal Destinations
    Background: Set Initial Data
        Given the "validators"
        """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "schema": {},
            "type": "text",
            "act": "correct",
            "_id": "correct_text"
        },
        {
            "schema": {},
            "type": "text",
            "act": "kill",
            "_id": "kill_text"
        }
        ]
        """
        When we post to "/products" with success
        """
        {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
        }
        """
        And we post to "/subscribers" with "digital" and success
        """
        {
        "name":"Channel 1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
        }
        """
        When we post to "/desks"
        """
        {"name": "Sports"}
        """
        Then we store "origin_desk" with value "#desks._id#" to context
        Then we store "origin_stage" with value "#desks.working_stage#" to context
        When we post to "desks"
        """
        {"name": "Features"}
        """
        Then we store "destination_desk" with value "#desks._id#" to context
        Then we store "destination_stage" with value "#desks.incoming_stage#" to context

    @auth
    Scenario: Create items for destinations on publish
        When we post to "archive" with success
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "Take-1 headline",
            "abstract": "Take-1 abstract",
            "task": {
                "user": "#CONTEXT_USER_ID#",
                "desk": "#origin_desk#",
                "stage": "#origin_stage#"
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
                "utc_publish_schedule": "2099-05-19T10:15:00+0000"
            }
        }]
        """
        Given "internal_destinations"
        """
        [{"name": "copy", "is_active": true, "desk": "#destination_desk#", "macro": "usd_to_cad"}]
        """
        When we publish "#archive._id#" with "publish" type and "published" state
        """
        {"publish_schedule": "2099-05-19T10:15:00",
        "schedule_settings": {"time_zone": "Europe/London"}}
        """
        Then we get OK response

        When we get "/archive"
        Then we get list with 1 items
        """
        {"_items": [{
            "state": "routed",
            "original_id": "#archive._id#",
            "family_id": "#archive._id#",
            "task": {"desk": "#destination_desk#", "stage": "#destination_stage#"},
            "body_html": "Body $10 (CAD 20)",
            "publish_schedule": "2099-05-19T10:15:00+0000",
            "schedule_settings": {
                "time_zone": "Europe/London",
                "utc_publish_schedule": "2099-05-19T10:15:00+0000"
            }
        }]}
        """
        When we get "/published"
        Then we get list with 1 items
        """
        {"_items": [{
            "state": "scheduled",
            "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
            "body_html": "Body $10",
            "publish_schedule": "2099-05-19T10:15:00+0000",
            "schedule_settings": {
                "time_zone": "Europe/London",
                "utc_publish_schedule": "2099-05-19T10:15:00+0000"
            }
        }]}
        """

    @auth
    Scenario: Create & Publish item for destinations on publish and overwrite the item on correction and kill
        When we post to "archive" with success
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "Take-1 headline",
            "abstract": "Take-1 abstract",
            "task": {
                "user": "#CONTEXT_USER_ID#",
                "desk": "#origin_desk#",
                "stage": "#origin_stage#"
            },
            "body_html": "Body",
            "state": "submitted",
            "slugline": "Take-1 slugline",
            "urgency": "4",
            "pubstatus": "usable",
            "subject":[{"qcode": "17004000", "name": "Statistics"}],
            "anpa_category": [{"qcode": "A", "name": "Sport"}],
            "anpa_take_key": "Take"
        }]
        """

        Given "internal_destinations"
        """
        [{"name": "publish", "is_active": true, "desk": "#desks._id#", "macro": "Internal_Destination_Auto_Publish"}]
        """

        When we publish "#archive._id#" with "publish" type and "published" state
        Then we get OK response

        When we get "/archive"
        Then we get list with 0 items
        When we get "/published"
        Then we get list with 2 items
        """
        {
            "_items": [
                {
                    "_id": "#archive._id#",
                    "state": "published",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body",
                    "_current_version": 2
                },
                {
                    "state": "published",
                    "task": {"desk": "#destination_desk#", "stage": "#destination_stage#"},
                    "body_html": "Body",
                    "original_id": "#archive._id#",
                    "processed_from": "#archive._id#",
                    "_current_version": 4
                }
            ]
        }
        """
        When we publish "#archive._id#" with "correct" type and "corrected" state
        """
        {
            "body_html": "Body Corrected"
        }
        """
        Then we get OK response
        When we get "/published"
        Then we get list with 4 items
        """
        {
            "_items": [
                {
                    "_id": "#archive._id#",
                    "state": "corrected",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body Corrected",
                    "_current_version": 3
                },
                {
                    "state": "corrected",
                    "task": {"desk": "#destination_desk#", "stage": "#destination_stage#"},
                    "body_html": "Body Corrected",
                    "original_id": "#archive._id#",
                    "processed_from": "#archive._id#",
                    "_current_version": 5
                },
                {
                    "_id": "#archive._id#",
                    "state": "published",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body",
                    "_current_version": 2
                },
                {
                    "state": "published",
                    "task": {"desk": "#destination_desk#", "stage": "#destination_stage#"},
                    "body_html": "Body",
                    "original_id": "#archive._id#",
                    "processed_from": "#archive._id#",
                    "_current_version": 4
                }
            ]
        }
        """
        When we publish "#archive._id#" with "kill" type and "killed" state
        Then we get OK response
        When we get "/published"
        Then we get list with 6 items
        """
        {
            "_items": [
                {
                    "_id": "#archive._id#",
                    "state": "killed",
                    "pubstatus": "canceled",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "_current_version": 4
                },
                {
                    "state": "killed",
                    "task": {"desk": "#destination_desk#", "stage": "#destination_stage#"},
                    "original_id": "#archive._id#",
                    "processed_from": "#archive._id#",
                    "_current_version": 6,
                    "pubstatus": "canceled"
                },
                {
                    "_id": "#archive._id#",
                    "state": "corrected",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body Corrected",
                    "_current_version": 3,
                    "pubstatus": "usable"
                },
                {
                    "state": "corrected",
                    "task": {"desk": "#destination_desk#", "stage": "#destination_stage#"},
                    "body_html": "Body Corrected",
                    "original_id": "#archive._id#",
                    "processed_from": "#archive._id#",
                    "_current_version": 5,
                    "pubstatus": "usable"
                },
                {
                    "_id": "#archive._id#",
                    "state": "published",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body",
                    "_current_version": 2,
                    "pubstatus": "usable"
                },
                {
                    "state": "published",
                    "task": {"desk": "#destination_desk#", "stage": "#destination_stage#"},
                    "body_html": "Body",
                    "original_id": "#archive._id#",
                    "processed_from": "#archive._id#",
                    "_current_version": 4,
                    "pubstatus": "usable"
                }
            ]
        }
        """

    @auth
    Scenario: Publishing an item from the same desk as internal destination desk should not create another item.
        When we post to "archive" with success
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "Take-1 headline",
            "abstract": "Take-1 abstract",
            "task": {
                "user": "#CONTEXT_USER_ID#",
                "desk": "#destination_desk#",
                "stage": "#destination_stage#"
            },
            "body_html": "Body",
            "state": "submitted",
            "slugline": "Take-1 slugline",
            "urgency": "4",
            "pubstatus": "usable",
            "subject":[{"qcode": "17004000", "name": "Statistics"}],
            "anpa_category": [{"qcode": "A", "name": "Sport"}],
            "anpa_take_key": "Take"
        }]
        """
        Given "internal_destinations"
        """
        [{"name": "copy", "is_active": true, "desk": "#destination_desk#", "macro": "Internal_Destination_Auto_Publish"}]
        """
        When we publish "#archive._id#" with "publish" type and "published" state
        Then we get OK response

        When we get "/archive"
        Then we get list with 0 items
        When we get "/published"
        Then we get list with 1 items
        """
        {
            "_items": [
                {
                    "_id": "#archive._id#",
                    "state": "published",
                    "task": {"desk": "#destination_desk#", "stage": "#destination_stage#"},
                    "body_html": "Body",
                    "_current_version": 2,
                    "pubstatus": "usable"
                }
            ]
        }
        """

    @auth
    Scenario: Processed from is not set when item is duplicated or updated.
        When we post to "archive" with success
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "Take-1 headline",
            "abstract": "Take-1 abstract",
            "task": {
                "user": "#CONTEXT_USER_ID#",
                "desk": "#destination_desk#",
                "stage": "#destination_stage#"
            },
            "body_html": "Body",
            "state": "submitted",
            "slugline": "Take-1 slugline",
            "urgency": "4",
            "pubstatus": "usable",
            "subject":[{"qcode": "17004000", "name": "Statistics"}],
            "anpa_category": [{"qcode": "A", "name": "Sport"}],
            "anpa_take_key": "Take"
        }]
        """
        Given "internal_destinations"
        """
        [{"name": "copy", "is_active": true, "desk": "#origin_desk#", "macro": "Internal_Destination_Auto_Publish"}]
        """
        When we publish "#archive._id#" with "publish" type and "published" state
        Then we get OK response
        When we get "/published?where=%7B%22processed_from%22%3A%22123%22%7D"
        Then we get list with 1 items
        Then we store "published_item" with first item
        When we rewrite "#published_item._id#"
        Then we get OK response
        When we get "/archive/#REWRITE_ID#"
        Then we get existing resource
        """
        {
            "rewrite_of": "#published_item._id#",
            "processed_from": "__no_value__"
        }
        """
        When we post to "/archive/#published_item._id#/duplicate"
        """
        {"desk": "#origin_desk#", "stage": "#origin_stage#", "type": "archive"}
        """
        Then we get OK response
        When we get "/archive/#duplicate._id#"
        Then we get existing resource
        """
        {
            "original_id": "#published_item._id#",
            "processed_from": "__no_value__"
        }
        """

    @auth
    Scenario: Create & Publish item for destinations on publish in global read off stage
        When we post to "archive" with success
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "Take-1 headline",
            "abstract": "Take-1 abstract",
            "task": {
                "user": "#CONTEXT_USER_ID#",
                "desk": "#origin_desk#",
                "stage": "#origin_stage#"
            },
            "body_html": "Body",
            "state": "submitted",
            "slugline": "Take-1 slugline",
            "urgency": "4",
            "pubstatus": "usable",
            "subject":[{"qcode": "17004000", "name": "Statistics"}],
            "anpa_category": [{"qcode": "A", "name": "Sport"}],
            "anpa_take_key": "Take"
        }]
        """
        When we post to "/stages" with success
        """
        {
            "name": "Invisible Stage",
            "desk": "#destination_desk#",
            "working_stage" : false,
            "default_incoming" : false,
            "is_visible" : false,
            "local_readonly" : true
        }
        """
        Given "internal_destinations"
        """
        [
            {
                "name": "publish",
                "is_active": true,
                "desk": "#destination_desk#",
                "macro": "Internal_Destination_Auto_Publish",
                "stage": "#stages._id#"
            }
        ]
        """

        When we publish "#archive._id#" with "publish" type and "published" state
        Then we get OK response
        When we get "/archive"
        Then we get list with 0 items
        When we get "/published"
        Then we get list with 1 items
        """
        {
            "_items": [
                {
                    "_id": "#archive._id#",
                    "state": "published",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body",
                    "_current_version": 2
                }
            ]
        }
        """
        When we patch "/desks/#destination_desk#"
        """
        {
            "members": [{"user": "#CONTEXT_USER_ID#"}]
        }
        """
        Then we get OK response
        When we get "/published"
        Then we get list with 2 items
        """
        {
            "_items": [
                {
                    "_id": "#archive._id#",
                    "state": "published",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body",
                    "_current_version": 2
                },
                {
                    "state": "published",
                    "task": {"desk": "#destination_desk#", "stage": "#stages._id#"},
                    "body_html": "Body",
                    "original_id": "#archive._id#",
                    "processed_from": "#archive._id#",
                    "_current_version": 4
                }
            ]
        }
        """
        When we patch "/desks/#destination_desk#"
        """
        {
            "members": []
        }
        """
        Then we get OK response
        When we publish "#archive._id#" with "correct" type and "corrected" state
        """
        {
            "body_html": "Body Corrected"
        }
        """
        Then we get OK response
        When we get "/published"
        Then we get list with 2 items
        """
        {
            "_items": [
                {
                    "_id": "#archive._id#",
                    "state": "corrected",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body Corrected",
                    "_current_version": 3
                },
                {
                    "_id": "#archive._id#",
                    "state": "published",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body",
                    "_current_version": 2
                }
            ]
        }
        """
        When we patch "/desks/#destination_desk#"
        """
        {
            "members": [{"user": "#CONTEXT_USER_ID#"}]
        }
        """
        Then we get OK response
        When we get "/published"
        Then we get list with 4 items
        """
        {
            "_items": [
                {
                    "_id": "#archive._id#",
                    "state": "corrected",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body Corrected",
                    "_current_version": 3
                },
                {
                    "_id": "#archive._id#",
                    "state": "published",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body",
                    "_current_version": 2
                },
                {
                    "state": "published",
                    "task": {"desk": "#destination_desk#", "stage": "#stages._id#"},
                    "body_html": "Body",
                    "original_id": "#archive._id#",
                    "processed_from": "#archive._id#",
                    "_current_version": 4
                },
                {
                    "state": "corrected",
                    "task": {"desk": "#destination_desk#", "stage": "#stages._id#"},
                    "body_html": "Body Corrected",
                    "original_id": "#archive._id#",
                    "processed_from": "#archive._id#",
                    "_current_version": 5
                }
            ]
        }
        """
        When we patch "/desks/#destination_desk#"
        """
        {
            "members": []
        }
        """
        Then we get OK response
        When we publish "#archive._id#" with "kill" type and "killed" state
        Then we get OK response
        When we get "/published"
        Then we get list with 3 items
        """
        {
            "_items": [
                {
                    "_id": "#archive._id#",
                    "state": "killed",
                    "pubstatus": "canceled",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "_current_version": 4
                },
                {
                    "_id": "#archive._id#",
                    "state": "corrected",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body Corrected",
                    "_current_version": 3,
                    "pubstatus": "usable"
                },
                {
                    "_id": "#archive._id#",
                    "state": "published",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body",
                    "_current_version": 2,
                    "pubstatus": "usable"
                }
            ]
        }
        """
        When we patch "/desks/#destination_desk#"
        """
        {
            "members": [{"user": "#CONTEXT_USER_ID#"}]
        }
        """
        Then we get OK response
        When we get "/published"
        Then we get list with 6 items
        """
        {
            "_items": [
                {
                    "_id": "#archive._id#",
                    "state": "killed",
                    "pubstatus": "canceled",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "_current_version": 4
                },
                {
                    "_id": "#archive._id#",
                    "state": "corrected",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body Corrected",
                    "_current_version": 3,
                    "pubstatus": "usable"
                },
                {
                    "_id": "#archive._id#",
                    "state": "published",
                    "task": {"desk": "#origin_desk#", "stage": "#origin_stage#"},
                    "body_html": "Body",
                    "_current_version": 2,
                    "pubstatus": "usable"
                },
                {
                    "state": "published",
                    "task": {"desk": "#destination_desk#", "stage": "#stages._id#"},
                    "body_html": "Body",
                    "original_id": "#archive._id#",
                    "processed_from": "#archive._id#",
                    "_current_version": 4,
                    "pubstatus": "usable"
                },
                {
                    "state": "corrected",
                    "task": {"desk": "#destination_desk#", "stage": "#stages._id#"},
                    "body_html": "Body Corrected",
                    "original_id": "#archive._id#",
                    "processed_from": "#archive._id#",
                    "_current_version": 5,
                    "pubstatus": "usable"
                },
                {
                    "state": "killed",
                    "task": {"desk": "#destination_desk#", "stage": "#stages._id#"},
                    "original_id": "#archive._id#",
                    "processed_from": "#archive._id#",
                    "_current_version": 6,
                    "pubstatus": "canceled"
                }
            ]
        }
        """

    @auth
    Scenario: Create items for destinations on publish and keep the state same as original item's state.
        When we post to "archive" with success
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "Take-1 headline",
            "abstract": "Take-1 abstract",
            "task": {
                "user": "#CONTEXT_USER_ID#",
                "desk": "#origin_desk#",
                "stage": "#origin_stage#"
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
                "utc_publish_schedule": "2099-05-19T10:15:00+0000"
            }
        }]
        """
        Given "internal_destinations"
        """
        [{"name": "copy", "is_active": true,  "desk": "#destination_desk#", "macro": "Internal_Destination_Auto_Publish"}]
        """
        When we publish "#archive._id#" with "publish" type and "scheduled" state
        """
        {
            "publish_schedule": "2099-05-19T10:15:00",
            "schedule_settings": {
                "time_zone": "Europe/London",
                "utc_publish_schedule": "2099-05-19T10:15:00+0000"
            }
        }
        """
        Then we get OK response
        When we get "/published?where=%7B%22processed_from%22%3A%22123%22%7D"
        Then we get list with 1 items
        """
        {
            "_items": [{
            "processed_from": "123",
            "format": "HTML",
            "operation": "publish",
            "family_id": "123",
            "state": "scheduled",
            "publish_schedule": "2099-05-19T10:15:00+0000",
            "pubstatus": "usable",
            "schedule_settings": {
                "time_zone": "Europe/London",
                "utc_publish_schedule": "2099-05-19T10:15:00+0000"
            }
            }]
        }
        """
        When we get "/published"
        Then we get list with 2 items

    @auth
    Scenario: Delay item creation for destinations on publish if the send_after_schedule is enabled for internal destinations
        When we post to "archive" with success
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "Take-1 headline",
            "abstract": "Take-1 abstract",
            "task": {
                "user": "#CONTEXT_USER_ID#",
                "desk": "#origin_desk#",
                "stage": "#origin_stage#"
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
                "utc_publish_schedule": "2099-05-19T10:15:00+0000"
            }
        }]
        """
        Given "internal_destinations"
        """
        [{"name": "copy", "is_active": true,  "desk": "#destination_desk#", "macro": "Internal_Destination_Auto_Publish",
        "send_after_schedule": true}]
        """
        When we publish "#archive._id#" with "publish" type and "scheduled" state
        """
        {
            "publish_schedule": "2099-05-19T10:15:00",
            "schedule_settings": {
                "time_zone": "Europe/London",
                "utc_publish_schedule": "2099-05-19T10:15:00+0000"
            }
        }
        """
        Then we get OK response
        When we get "/published?where=%7B%22processed_from%22%3A%22123%22%7D"
        Then we get list with 0 items
        When we get "/published"
        Then we get list with 1 items

