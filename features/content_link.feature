Feature: Link content in takes

    @auth
    Scenario: Send Content and continue from personal space
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        When we post to "archive"
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "abstract" : "abstract",
            "anpa_take_key": null,
            "guid": "123",
            "state": "draft",
            "task": {
                "user": "#CONTEXT_USER_ID#"
            },
            "priority": 1,
            "urgency": 1,
            "ednote": "ednote",
            "place": [{"is_active": true, "name": "ACT", "qcode": "ACT",
                  "state": "Australian Capital Territory",
                  "country": "Australia", "world_region": "Oceania"}]
        }]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we post to "archive/123/link"
        """
        [{}]
        """
        Then we get next take as "TAKE"
        """
        {
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "=2",
            "state": "draft",
            "priority": 1,
            "urgency": 1,
            "ednote": "ednote",
            "place": [{"is_active": true, "name": "ACT", "qcode": "ACT",
                  "state": "Australian Capital Territory",
                  "country": "Australia", "world_region": "Oceania"}],
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we get "archive"
        Then we get list with 3 items
        """
        {
            "_items": [
                {
                    "groups": [
                        {"id": "root", "refs": [{"idRef": "main"}]},
                        {
                            "id": "main",
                            "refs": [
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "123",
                                    "sequence": 1
                                },
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "#TAKE#",
                                    "sequence": 2
                                }
                            ]
                        }
                    ],
                    "type": "composite",
                    "package_type": "takes",
                    "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"},
                    "sequence": 2,
                    "_current_version": 1
                },
                {
                    "_id": "#TAKE#",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}],
                    "takes": {}
                },
                {
                    "guid": "123",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}],
                    "takes": {}
                }
            ]
        }
        """
        When we post to "archive/#TAKE#/link"
        """
        [{}]
        """
        Then we get next take as "TAKE2"
        """
        {
            "_id": "#TAKE2#",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "=3",
            "state": "draft",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we get "archive"
        Then we get list with 4 items
        """
        {
            "_items": [
                {
                    "groups": [
                        {"id": "root", "refs": [{"idRef": "main"}]},
                        {
                            "id": "main",
                            "refs": [
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "123",
                                    "sequence": 1
                                },
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "sequence": 2
                                }
                            ]
                        }
                    ],
                    "type": "composite",
                    "package_type": "takes",
                    "_current_version": 2
                },
                {
                    "_id": "#TAKE#",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}],
                    "takes": {}
                },
                {
                    "guid": "123",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}],
                    "takes": {}
                },
                {
                    "_id": "#TAKE2#",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}],
                    "takes": {}
                }
            ]
        }
        """
        When we post to "archive"
        """
        [{
            "guid": "456",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "abstract" : "abstract",
            "guid": "456",
            "state": "draft",
            "task": {
                "user": "#CONTEXT_USER_ID#"
            },
            "priority": 1,
            "urgency": 1,
            "ednote": "ednote",
            "place": [{"is_active": true, "name": "ACT", "qcode": "ACT",
                  "state": "Australian Capital Territory",
                  "country": "Australia", "world_region": "Oceania"}]
        }]
        """
        And we post to "/archive/456/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we post to "archive/456/link"
        """
        [{}]
        """
        Then we get next take as "TAKE"
        """
        {
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "=2",
            "state": "draft",
            "priority": 1,
            "urgency": 1,
            "ednote": "ednote",
            "place": [{"is_active": true, "name": "ACT", "qcode": "ACT",
                  "state": "Australian Capital Territory",
                  "country": "Australia", "world_region": "Oceania"}],
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """

    @auth
    Scenario: Metadata is copied from published takes
        Given the "validators"
        """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}}]
        """
    	And empty "ingest"
    	And "desks"
        """
        [{"name": "Sports"}]
        """
        When we post to "/products" with success
        """
        {
            "name":"prod-1","codes":"abc,xyz", "product_type": "both"
        }
        """
        And we post to "/subscribers" with success
        """
        {
          "name":"News1","media_type":"media", "subscriber_type": "wire",
          "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "products": ["#products._id#"],
          "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP","config":{"ip":"144.122.244.55","password":"xyz"}}]
        }
        """
    	And we post to "archive" with success
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "Take-1 headline",
            "abstract": "Take-1 abstract",
            "task": {
                "user": "#CONTEXT_USER_ID#"
            },
            "body_html": "Take-1",
            "state": "draft",
            "slugline": "Take-1 slugline",
            "urgency": "4",
            "pubstatus": "usable",
            "subject":[{"qcode": "17004000", "name": "Statistics"}],
            "anpa_category": [{"qcode": "A", "name": "Sport"}],
            "anpa_take_key": "Take"
        }]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we post to "archive/123/link"
        """
        [{}]
        """
        Then we get next take as "TAKE"
        """
        {
            "_id": "#TAKE#",
            "type": "text",
            "headline": "Take-1 headline",
            "slugline": "Take-1 slugline",
            "anpa_take_key": "Take=2",
            "state": "draft",
            "abstract": "__no_value__",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we patch "/archive/#TAKE#"
        """
        {"body_html": "Take-2"}
        """
        And we post to "/archive/#TAKE#/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
		And we get "/archive"
        Then we get list with 3 items
        When we publish "123" with "publish" type and "published" state
        Then we get OK response
        When we get "/archive/#TAKE_PACKAGE#"
        Then we get existing resource
        """
        {
            "type": "composite",
            "headline": "Take-1 headline",
            "slugline": "Take-1 slugline",
            "abstract": "Take-1 abstract"
        }
        """
        When we post to "archive/#TAKE#/link"
        """
        [{}]
        """
        Then we get next take as "TAKE2"
        """
        {
            "_id": "#TAKE2#",
            "type": "text",
            "headline": "Take-1 headline",
            "slugline": "Take-1 slugline",
            "anpa_take_key": "Take=3",
            "state": "draft",
            "abstract": "__no_value__",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we patch "/archive/#TAKE#"
        """
        {"body_html": "Take-2", "abstract": "Take-1 abstract changed", "state": "in_progress"}
        """
        And we post to "/archive/#TAKE#/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        And we publish "#TAKE#" with "publish" type and "published" state
        Then we get OK response
        When we get "/archive/#TAKE_PACKAGE#"
        Then we get existing resource
        """
        {
            "type": "composite",
            "headline": "Take-1 headline",
            "slugline": "Take-1 slugline",
            "abstract": "Take-1 abstract changed"
        }
        """
	    When we enqueue published
        When we get "/publish_queue"
        Then we get "Take-1 headline=2" in formatted output

    @auth
    Scenario: In a takes packages only last take can be spiked.
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        When we post to "archive"
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "Take",
            "guid": "123",
            "state": "draft",
            "task": {
                "user": "#CONTEXT_USER_ID#"
            }
        }]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we post to "archive/123/link"
        """
        [{}]
        """
        Then we get next take as "TAKE2"
        """
        {
            "_id": "#TAKE2#",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "Take=2",
            "state": "draft",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we get "archive"
        Then we get list with 3 items
        """
        {
            "_items": [
                {
                    "groups": [
                        {"id": "root", "refs": [{"idRef": "main"}]},
                        {
                            "id": "main",
                            "refs": [
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "123",
                                    "sequence": 1
                                },
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "#TAKE2#",
                                    "sequence": 2
                                }
                            ]
                        }
                    ],
                    "type": "composite",
                    "package_type": "takes",
                    "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"},
                    "sequence": 2,
                    "last_take": "__any_value__"
                },
                {
                    "_id": "#TAKE2#",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}],
                    "takes": {}
                },
                {
                    "guid": "123",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}],
                    "takes": {}
                }
            ]
        }
        """
        When we post to "archive/#TAKE2#/link"
        """
        [{}]
        """
        Then we get next take as "LAST_TAKE"
        """
        {
            "_id": "#LAST_TAKE#",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "Take=3",
            "state": "draft",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we get "archive"
        Then we get list with 4 items
        """
        {
            "_items": [
                {
                    "groups": [
                        {"id": "root", "refs": [{"idRef": "main"}]},
                        {
                            "id": "main",
                            "refs": [
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "123",
                                    "sequence": 1
                                },
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "#TAKE2#",
                                    "sequence": 2
                                },
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "#LAST_TAKE#",
                                    "sequence": 3
                                }
                            ]
                        }
                    ],
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 3
                },
                {
                    "_id": "#TAKE2#",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}]
                },
                {
                    "guid": "123",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}]
                },
                {
                    "_id": "#LAST_TAKE#",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}]
                }
            ]
        }
        """
        When we spike "#TAKE2#"
        Then we get response code 400
        """
        {"_issues": {"validator exception": "400: Only last take of the package can be spiked."}, "_status": "ERR"}
        """
        When we spike "123"
        Then we get response code 400
        """
        {"_issues": {"validator exception": "400: Only last take of the package can be spiked."}, "_status": "ERR"}
        """
        When we spike "#LAST_TAKE#"
        Then we get OK response
        And we get spiked content "#LAST_TAKE#"
        When we get "archive"
        Then we get list with 4 items
        """
        {
            "_items": [
                {
                    "groups": [
                        {"id": "root", "refs": [{"idRef": "main"}]},
                        {
                            "id": "main",
                            "refs": [
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "123",
                                    "sequence": 1
                                },
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "#TAKE2#",
                                    "sequence": 2
                                }
                            ]
                        }
                    ],
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 2
                },
                {
                    "_id": "#TAKE2#",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}]
                },
                {
                    "guid": "123",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}]
                },
                {
                    "_id": "#LAST_TAKE#",
                    "headline": "test1",
                    "type": "text",
                    "state": "spiked"
                }
            ]
        }
        """
        When we spike "#TAKE2#"
        Then we get OK response
        And we get spiked content "#TAKE2#"
        When we spike "123"
        Then we get OK response
        And we get spiked content "123"
        When we get "/archive/#TAKE_PACKAGE#"
        Then we get response code 404

    @auth
    Scenario: Killing a takes packages spikes all unpublished takes.
        Given the "validators"
        """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
        {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
        """
    	And empty "ingest"
    	And "desks"
        """
        [{"name": "Sports"}]
        """
        When we post to "/products" with success
        """
        {
            "name":"prod-1","codes":"abc,xyz", "product_type": "both"
        }
        """
        And we post to "/subscribers" with success
        """
        {
          "name":"News1","media_type":"media", "subscriber_type": "digital",
          "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "products": ["#products._id#"],
          "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP","config":{"ip":"144.122.244.55","password":"xyz"}}]
        }
        """
    	And we post to "archive" with success
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "test1",
            "abstract": "Take-1 abstract",
            "task": {
                "user": "#CONTEXT_USER_ID#"
            },
            "body_html": "Take-1",
            "state": "draft",
            "slugline": "comics",
            "urgency": "4",
            "pubstatus": "usable",
            "subject":[{"qcode": "17004000", "name": "Statistics"}],
            "anpa_category": [{"qcode": "A", "name": "Sport"}],
            "anpa_take_key": "Take"
        }]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we post to "archive/123/link"
        """
        [{}]
        """
        Then we get next take as "TAKE2"
        """
        {
            "_id": "#TAKE2#",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "Take=2",
            "state": "draft",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we post to "/archive/#TAKE2#/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we get "archive/#TAKE_PACKAGE#"
        Then we get existing resource
        """
        {
            "last_take": "#TAKE2#",
            "sequence": 2,
            "_current_version": 1,
            "groups":[
                        {"id": "root", "refs": [{"idRef": "main"}]},
                        {
                            "id": "main",
                            "refs": [
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "123",
                                    "sequence": 1
                                },
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "#TAKE2#",
                                    "sequence": 2
                                }
                            ]
                        }
                ]
        }
        """
        When we post to "archive/#TAKE2#/link"
        """
        [{}]
        """
        Then we get next take as "TAKE3"
        """
        {
            "_id": "#TAKE3#",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "Take=3",
            "state": "draft",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we post to "/archive/#TAKE3#/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        And we get "archive/#TAKE_PACKAGE#" and match
        """
        {
            "last_take": "#TAKE3#",
            "sequence": 3,
            "_current_version": 2
        }
        """
        When we publish "123" with "publish" type and "published" state
        Then we get OK response
        When we publish "123" with "kill" type and "killed" state
        Then we get OK response
        And we get "/archive/#TAKE2#" and match
        """
        {
            "_id": "#TAKE2#",
            "state": "spiked"
        }
        """
        And we get "/archive/#TAKE3#" and match
        """
        {
            "_id": "#TAKE3#",
            "state": "spiked"
        }
        """
        And we get "/archive/#TAKE_PACKAGE#" and match
        """
        {
            "last_take": "123",
            "sequence": 1,
            "_current_version": 6,
            "groups":[
                        {"id": "root", "refs": [{"idRef": "main"}]},
                        {
                            "id": "main",
                            "refs": [
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "123",
                                    "sequence": 1
                                }
                            ]
                        }
                ]
        }
        """

    @auth
    Scenario: If the user is the member of a desk then New Take on a desk is allowed
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        When we post to "archive"
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "abstract" : "abstract",
            "anpa_take_key": "Take",
            "guid": "123",
            "state": "draft",
            "task": {
                "user": "#CONTEXT_USER_ID#"
            },
            "priority": 1,
            "urgency": 1,
            "ednote": "ednote",
            "place": [{"is_active": true, "name": "ACT", "qcode": "ACT",
                  "state": "Australian Capital Territory",
                  "country": "Australia", "world_region": "Oceania"}]
        }]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we post to "archive/123/link"
        """
        [{"desk": "#desks._id#"}]
        """
        Then we get error 403
        """
        {"_message": "No privileges to create new take on requested desk.", "_status": "ERR"}
        """
        When we patch "desks/#desks._id#"
        """
        {"members": [{"user": "#CONTEXT_USER_ID#"}]}
        """
        Then we get OK response
        When we post to "archive/123/link"
        """
        [{"desk": "#desks._id#"}]
        """
        Then we get next take as "TAKE2"
        """
        {
            "_id": "#TAKE2#",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "Take=2",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}],
            "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#"},
            "priority": 1,
            "urgency": 1,
            "ednote": "ednote",
            "place": [{"is_active": true, "name": "ACT", "qcode": "ACT",
                  "state": "Australian Capital Territory",
                  "country": "Australia", "world_region": "Oceania"}]
        }
        """

    @auth
    Scenario: Link a story as the second take of another story
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        When we post to "archive"
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "abstract" : "abstract",
            "state": "draft",
            "task": {
                "user": "#CONTEXT_USER_ID#"
            },
            "priority": 5,
            "urgency": 4,
            "ednote": "ednote",
            "place": [{"is_active": true, "name": "ACT", "qcode": "ACT",
                  "state": "Australian Capital Territory",
                  "country": "Australia", "world_region": "Oceania"}]
        },
        {
            "guid": "456",
            "type": "text",
            "headline": "test2",
            "slugline": "comics2",
            "abstract" : "abstract",
            "state": "draft",
            "task": {
                "user": "#CONTEXT_USER_ID#"
            },
            "priority": 1,
            "urgency": 1,
            "ednote": "ednote",
            "place": [{"is_active": true, "name": "ACT", "qcode": "ACT",
                  "state": "Australian Capital Territory",
                  "country": "Australia", "world_region": "Oceania"}]
        }]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we post to "archive/123/link"
        """
        [{"link_id": "456"}]
        """
        Then we get next take as "TAKE"
        """
        {
            "_id": "456",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "=2",
            "state": "draft",
            "priority": 5,
            "urgency": 4,
            "ednote": "ednote",
            "place": [{"is_active": true, "name": "ACT", "qcode": "ACT",
                  "state": "Australian Capital Territory",
                  "country": "Australia", "world_region": "Oceania"}],
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we get "archive"
        Then we get list with 3 items
        """
        {
            "_items": [
                {
                    "groups": [
                        {"id": "root", "refs": [{"idRef": "main"}]},
                        {
                            "id": "main",
                            "refs": [
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "123",
                                    "sequence": 1
                                },
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "456",
                                    "sequence": 2
                                }
                            ]
                        }
                    ],
                    "type": "composite",
                    "package_type": "takes",
                    "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"},
                    "sequence": 2,
                    "_current_version": 1
                },
                {
                    "_id": "456",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}],
                    "takes": {}
                },
                {
                    "guid": "123",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}],
                    "takes": {}
                }
            ]
        }
        """

    @auth
    Scenario: Link a story as the next take of an existing take story
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        When we post to "archive"
          """
          [{
              "guid": "123",
              "type": "text",
              "headline": "test1",
              "slugline": "comics",
              "anpa_take_key": "Take",
              "state": "draft",
              "subject":[{"qcode": "17004000", "name": "Statistics"}],
              "task": {
                  "user": "#CONTEXT_USER_ID#"
              },
              "body_html": "Take-1"
          },
            {
                "guid": "456",
                "type": "text",
                "headline": "test2",
                "slugline": "comics2",
                "abstract" : "abstract",
                "state": "submitted",
                "subject":[{"qcode": "123456789", "name": "Finance"}],
                "task": {
                    "user": "#CONTEXT_USER_ID#"
                },
                "priority": 1,
                "urgency": 1,
                "ednote": "ednote",
                "place": [{"is_active": true, "name": "ACT", "qcode": "ACT",
                      "state": "Australian Capital Territory",
                      "country": "Australia", "world_region": "Oceania"}]
            }]
          """
          And we post to "/archive/123/move"
          """
          [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
          """
          Then we get OK response
          When we post to "archive/123/link"
          """
          [{}]
          """
          Then we get next take as "TAKE"
          """
          {
              "type": "text",
              "headline": "test1",
              "slugline": "comics",
              "anpa_take_key": "Take=2",
              "subject":[{"qcode": "17004000", "name": "Statistics"}],
              "state": "draft",
              "original_creator": "#CONTEXT_USER_ID#"
          }
          """
        When we post to "archive/#TAKE#/link"
        """
        [{"link_id": "456"}]
        """
        Then we get next take as "TAKE"
        """
        {
            "_id": "456",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "Take=3",
            "state": "submitted",
            "priority": 6,
            "urgency": 3,
            "ednote": "ednote",
            "place": [],
            "original_creator": "#CONTEXT_USER_ID#",
            "subject":[{"qcode": "17004000", "name": "Statistics"}],
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we get "archive"
        Then we get list with 4 items
        """
        {
            "_items": [
                {
                    "groups": [
                        {
                            "id": "main",
                            "refs": [
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "123",
                                    "sequence": 1
                                },
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "456",
                                    "sequence": 3
                                }
                            ]
                        }
                    ],
                    "type": "composite",
                    "package_type": "takes",
                    "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"},
                    "sequence": 3,
                    "_current_version": 2
                },
                {
                    "_id": "456",
                    "headline": "test1",
                    "type": "text",
                    "state": "submitted",
                    "linked_in_packages": [{"package_type": "takes"}],
                    "takes": {}
                },
                {
                    "guid": "123",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}],
                    "takes": {}
                }
            ]
        }
        """

    @auth @test
    Scenario: Unlink an update of an unpublished story
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{
              "guid": "123",
              "type": "text",
              "headline": "test1",
              "slugline": "comics",
              "state": "fetched",
              "subject":[{"qcode": "17004000", "name": "Statistics"}],
              "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
              "body_html": "Story-1"
        }]
        """
        When we rewrite "123"
        """
            {"desk_id": "#desks._id#"}
        """
        When we get "/archive/#REWRITE_ID#"
        Then we get existing resource
        """
        {
            "_id": "#REWRITE_ID#",
            "rewrite_of": "123",
            "headline": "test1",
            "rewrite_sequence": 1,
            "anpa_take_key": "update"
        }
        """
        When we get "/archive/123"
        Then we get existing resource
        """
        {
            "_id": "123",
            "rewritten_by": "#REWRITE_ID#"
        }
        """
        When we delete link "archive/#REWRITE_ID#/link"
        Then we get response code 204
        When we get "/archive/#REWRITE_ID#"
        Then we get "rewrite_of" not populated
        And we get "anpa_take_key" not populated
        And we get "rewrite_sequence" not populated
        When we get "/archive/123"
        Then we get "rewritten_by" not populated

    @auth
    Scenario: Unlink an update of a published story
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        And "validators"
        """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
        """
        And "archive"
        """
        [{
              "guid": "123",
              "type": "text",
              "headline": "test1",
              "slugline": "comics",
              "state": "fetched",
              "subject":[{"qcode": "17004000", "name": "Statistics"}],
              "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
              "body_html": "Story-1"
        }]
        """
        When we publish "123" with "publish" type and "published" state
        Then we get OK response
        When we rewrite "123"
        """
            {"desk_id": "#desks._id#"}
        """
        When we get "/archive/#REWRITE_ID#"
        Then we get existing resource
        """
        {
            "_id": "#REWRITE_ID#",
            "rewrite_of": "#archive.123.take_package#",
            "headline": "test1",
            "rewrite_sequence": 1,
            "anpa_take_key": "update"
        }
        """
        When we get "/archive/123"
        Then we get existing resource
        """
        {
            "_id": "123",
            "rewritten_by": "#REWRITE_ID#"
        }
        """
        When we delete link "archive/#REWRITE_ID#/link"
        Then we get response code 204
        When we get "/archive/#REWRITE_ID#"
        Then we get "rewrite_of" not populated
        And we get "anpa_take_key" not populated
        And we get "rewrite_sequence" not populated
        When we get "/archive/123"
        Then we get "rewritten_by" not populated
        When we get "/published/123"
        Then we get "rewritten_by" not populated

    @auth
    Scenario: Unlink the last take
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        When we post to "archive"
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "Take",
            "guid": "123",
            "state": "draft",
            "task": {
                "user": "#CONTEXT_USER_ID#"
            }
        }]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we post to "archive/123/link"
        """
        [{}]
        """
        Then we get next take as "TAKE2"
        """
        {
            "_id": "#TAKE2#",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "Take=2",
            "state": "draft",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """

        When we delete link "archive/#TAKE2#/link"
        Then we get response code 204
        When we get "archive"
        Then we get list with 3 items
        """
        {
            "_items": [
                {
                    "groups": [
                        {"id": "root", "refs": [{"idRef": "main"}]},
                        {
                            "id": "main",
                            "refs": [
                                {
                                    "headline": "test1",
                                    "slugline": "comics",
                                    "residRef": "123",
                                    "sequence": 1
                                }
                            ]
                        }
                    ],
                    "type": "composite",
                    "package_type": "takes",
                    "sequence": 1
                },
                {
                    "guid": "123",
                    "headline": "test1",
                    "type": "text",
                    "linked_in_packages": [{"package_type": "takes"}]
                }
            ]
        }
        """
        When we get "/archive/#TAKE2#"
        Then we get existing resource
        """
        {
          "linked_in_packages": []
        }
        """
        And we get "sequence" not populated
        And we get "anpa_take_key" not populated

    @auth
    Scenario: Unlink the non-last take fails
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        When we post to "archive"
        """
        [{
            "guid": "123",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "Take",
            "guid": "123",
            "state": "draft",
            "task": {
                "user": "#CONTEXT_USER_ID#"
            }
        }]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we post to "archive/123/link"
        """
        [{}]
        """
        Then we get next take as "TAKE2"
        """
        {
            "_id": "#TAKE2#",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "Take=2",
            "state": "draft",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we post to "archive/#TAKE2#/link"
        """
        [{}]
        """
        Then we get next take as "LAST_TAKE"
        """
        {
            "_id": "#LAST_TAKE#",
            "type": "text",
            "headline": "test1",
            "slugline": "comics",
            "anpa_take_key": "Take=3",
            "state": "draft",
            "original_creator": "#CONTEXT_USER_ID#",
            "takes": {
                "_id": "#TAKE_PACKAGE#",
                "package_type": "takes",
                "type": "composite"
            },
            "linked_in_packages": [{"package_type" : "takes","package" : "#TAKE_PACKAGE#"}]
        }
        """
        When we get "archive"
        Then we get list with 4 items
        When we delete link "archive/#TAKE2#/link"
        Then we get error 400
        """
        {"_message": "Only the last take can be unlinked!"}
        """

    @auth
    Scenario: Unlink ignores item in a normal package
        Given empty "archive"
        And "desks"
        """
        [{"name": "test desk"}]
        """
        When we post to "archive" with success
        """
        [{"headline": "test", "guid": "123", "slugline": "WORMS"},
         {"headline": "test", "guid": "456", "slugline": "SNAILS"}]
        """
        When we post to "archive" with success
        """
        {
            "groups": [
                {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                {
                    "id": "main",
                    "refs": [
                        {
                            "headline": "test package with text",
                            "residRef": "123",
                            "slugline": "WORMS"
                        },
                        {
                            "headline": "test package with text",
                            "residRef": "456",
                            "slugline": "SNAILS"
                        }
                    ],
                    "role": "grpRole:Main"
                }
            ],
            "guid": "789",
            "type": "composite",
            "task": {"user": "#user._id#", "desk": "#desks._id#"}
        }
        """
        When we delete link "archive/456/link"
        Then we get error 400
        """
        {"_message": "Only takes and updates can be unlinked!"}
        """

