Feature: Ingest Rule Handlers

    @auth
    Scenario: Get list of available rule handlers
        When we get "/ingest_rule_handlers"
        Then we get list with 2 items
        """
        {"_items": [
            {
                "_id": "desk_fetch_publish",
                "name": "Desk Fetch/Publish",
                "supported_actions": {
                    "fetch_to_desk": true,
                    "publish_from_desk": true
                },
                "supported_configs": {
                    "exit": true,
                    "preserve_desk": true
                },
                "default_values": {
                    "name": "",
                    "filter": null,
                    "handler": "desk_fetch_publish",
                    "actions": {
                        "fetch": [],
                        "publish": [],
                        "exit": false
                    },
                    "schedule": {
                        "day_of_week": [
                            "MON",
                            "TUE",
                            "WED",
                            "THU",
                            "FRI",
                            "SAT",
                            "SUN"
                        ],
                        "hour_of_day_from": null,
                        "hour_of_day_to": null,
                        "_allDay": true
                    }
                }
            },
            {
                "_id": "planning_publish",
                "name": "Autopost Planning",
                "supported_actions": {
                    "fetch_to_desk": false,
                    "publish_from_desk": false
                },
                "supported_configs": {
                    "exit": true,
                    "preserve_desk": false
                },
                "default_values": {
                    "name": "",
                    "filter": null,
                    "handler": "planning_publish",
                    "actions": {
                        "fetch": [],
                        "publish": [],
                        "exit": false,
                        "extra": {
                            "autopost": true
                        }
                    },
                    "schedule": {
                        "day_of_week": [
                            "MON",
                            "TUE",
                            "WED",
                            "THU",
                            "FRI",
                            "SAT",
                            "SUN"
                        ],
                        "hour_of_day_from": null,
                        "hour_of_day_to": null,
                        "_allDay": true
                    }
                }
            }
        ]}
        """
