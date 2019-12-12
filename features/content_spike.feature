Feature: Content Spiking

    @auth
    @notification
    Scenario: Spike a user content and validate metadata set by API
        Given "archive"
        """
        [{"_id": "item-1", "guid": "item-1", "headline": "test",
        "_current_version": 1, "state": "draft", "event_id": "abc123"}]
        """
        When we get "/archive/item-1"
        Then we get latest
        """
        {"_id": "item-1", "state": "draft", "sign_off": "abc"}
        """
        When we spike "item-1"
        Then we get OK response
        And we get spiked content "item-1"
        And we get notifications
        """
        [{"event": "item:spike", "extra": {"item": "item-1", "user": "#CONTEXT_USER_ID#"}}]
        """
        And we get version 2
        And we get global content expiry
        When we get "/archive/item-1"
        Then we get existing resource
        """
        {"_id": "item-1", "state": "spiked", "sign_off": "abc"}
        """
        And the field "event_id" value is not "abc123"

    @auth
    Scenario: Spike a desk content
        Given empty "desks"
        Given empty "archive"
        Given empty "stages"
        Given "desks"
        """
        [{"name": "Sports Desk", "content_expiry": 60}]
        """
        Given "archive"
        """
        [{"_id": "item-1", "guid": "item-1", "_current_version": 1, "headline": "test", "task":{"desk":"#desks._id#", "stage" :"#desks.incoming_stage#"}}]
        """
        When we spike "item-1"
        Then we get OK response
        And we get spiked content "item-1"
        And we get version 2
        And we get desk spike expiry after "60"
        When we get "/archive/item-1"
        Then we get existing resource
        """
        {"_id": "item-1", "state": "spiked", "sign_off": "abc"}
        """

    @auth
    @provider
    Scenario: Spike fetched content
        Given empty "archive"
        Given "desks"
        """
        [{"name": "Sports Desk"}]
        """
        And ingest from "reuters"
        """
        [{"guid": "tag:reuters.com,2014:newsml_LOVEA6M0L7U2E"}]
        """
        When we post to "/ingest/tag:reuters.com,2014:newsml_LOVEA6M0L7U2E/fetch"
        """
        {"desk": "#desks._id#"}
        """
        Then we get "_id"
        When we spike fetched item
        """
        {"_id": "#_id#"}
        """
        Then we get OK response

    @auth
    @notification
    Scenario: Unspike a content
        Given empty "archive"
        Given we have "administrator" as type of user
        Given "archive"
        """
        [{"_id": "item-1", "guid": "item-1", "_current_version": 1, "headline": "test", "state": "draft"}]
        """
        When we spike "item-1"
        And we unspike "item-1"
        Then we get unspiked content "item-1"
        And we get notifications
        """
        [{"event": "item:unspike", "extra": {"item": "item-1", "user": "#CONTEXT_USER_ID#"}}]
        """
        And we get version 3
        And we get global content expiry

    @auth
    Scenario: Unspike a desk content
        Given empty "desks"
        Given empty "archive"
        Given empty "stages"
        Given "desks"
        """
        [{"name": "Sports Desk", "content_expiry": 60}]
        """
        Given "archive"
        """
        [{"_id": "item-1", "guid": "item-1", "_current_version": 1, "headline": "test", "task":{"desk":"#desks._id#", "stage" :"#desks.incoming_stage#"}}]
        """
        When we spike "item-1"
        And we unspike "item-1"
        Then we get unspiked content "item-1"
        And we get version 3
        And we get desk spike expiry after "60"

    @auth
    Scenario: Unspike a desk content to different desk
        Given "desks"
        """
        [{"name": "sports"}]
        """
        Given "archive"
        """
        [{"_id": "item-1", "guid": "item-1", "_current_version": 1, "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        When we spike "item-1"
        When we post to "desks"
        """
        [{"name": "finance"}]
        """
        When we unspike "item-1"
        """
        {"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
        """
        Then we get unspiked content "item-1"
        """
        {"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
        """

    @auth
    Scenario: Sign Off changes when content is spiked or unspiked
        Given "desks"
        """
        [{"name": "Sports Desk", "content_expiry": 60}]
        """
        When we post to "/archive" with success
        """
        [{"guid": "item-1", "headline": "test", "task":{"desk":"#desks._id#", "stage" :"#desks.incoming_stage#"}}]
        """
        Then we get new resource
        """
        {"sign_off": "abc"}
        """
        When we switch user
        And we spike "#archive._id#"
        Then we get OK response
        When we get "/archive/#archive._id#"
        Then we get existing resource
        """
        {"sign_off": "abc/foo"}
        """
        When we login as user "bar" with password "foobar" and user type "admin"
        """
        {"sign_off": "bar"}
        """
        And we unspike "#archive._id#"
        Then we get OK response
        When we get "/archive/#archive._id#"
        Then we get existing resource
        """
        {"sign_off": "abc/foo/bar"}
        """

    @auth
    Scenario: Spike a non-empty package
        Given empty "archive"
        And "desks"
        """
        [{"name": "test desk"}]
        """
        Given "archive"
        """
        [{"headline": "test", "_id": "item-1", "guid": "item-1", "slugline": "WORMS", "linked_in_packages": [{"package": "package-1"}]}]
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
                            "residRef": "item-1",
                            "slugline": "awesome article"
                        }
                    ],
                    "role": "grpRole:Main"
                }
            ],
            "_id": "package-1",
            "guid": "package-1",
            "type": "composite",
            "task": {"user": "#user._id#", "desk": "#desks._id#"}
        }
        """
        When we spike "package-1"
        Then we get OK response
        When we get "/archive/package-1"
        Then we get existing resource
        """
        {
            "deleted_groups": [
                {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                {
                    "id": "main",
                    "refs": [
                        {
                            "headline": "test package with text",
                            "residRef": "item-1",
                            "slugline": "awesome article"
                        }
                    ],
                    "role": "grpRole:Main"
                }
            ],
            "groups": [],
            "_id": "package-1",
            "guid": "package-1",
            "type": "composite"
        }
        """
        When we get "/archive/item-1"
        Then we get existing resource
        """
        {"linked_in_packages": []}
        """
        When we spike "item-1"
        Then we get OK response

    @auth
    Scenario: Unspike a non-empty package
        Given empty "archive"
        And "desks"
        """
        [{"name": "test desk"}]
        """
        Given "archive"
        """
        [{"headline": "test", "_id": "item-1", "guid": "item-1", "slugline": "WORMS", "linked_in_packages": []}]
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
                            "residRef": "item-1",
                            "slugline": "awesome article"
                        }
                    ],
                    "role": "grpRole:Main"
                }
            ],
            "_id": "package-1",
            "guid": "package-1",
            "type": "composite",
            "task": {"user": "#user._id#", "desk": "#desks._id#"}
        }
        """
        When we spike "package-1"
        Then we get OK response
        When we unspike "package-1"
        Then we get OK response
        When we get "/archive/package-1"
        Then we get existing resource
        """
        {
            "groups": [
                {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                {
                    "id": "main",
                    "refs": [
                        {
                            "headline": "test package with text",
                            "residRef": "item-1",
                            "slugline": "awesome article"
                        }
                    ],
                    "role": "grpRole:Main"
                }
            ],
            "deleted_groups": [],
            "_id": "package-1",
            "guid": "package-1",
            "type": "composite"
        }
        """
        When we get "/archive/item-1"
        Then we get existing resource
        """
        {"linked_in_packages": [{"package": "package-1"}]}
        """

    @auth
    Scenario: Spike a desk content with configured spike expiry
        Given empty "desks"
        Given empty "archive"
        Given empty "stages"
        Given "desks"
        """
        [{"name": "Sports Desk", "content_expiry": 60}]
        """
        Given "archive"
        """
        [{"_id": "item-1", "guid": "item-1", "_current_version": 1, "headline": "test", "task":{"desk":"#desks._id#", "stage" :"#desks.incoming_stage#"}}]
        """
        Then we set spike exipry "70"
        When we spike "item-1"
        Then we get OK response
        And we get spiked content "item-1"
        And we get version 2
        And we get desk spike expiry after "70"
        When we get "/archive/item-1"
        Then we get existing resource
        """
        {"_id": "item-1", "state": "spiked", "sign_off": "abc"}
        """

    @auth
    @notification
    Scenario: Spike locked item
        Given "archive"
        """
        [{"_id": "item-1", "guid": "item-1", "headline": "test",
        "_current_version": 1, "state": "draft", "event_id": "abc123"}]
        """

        When we post to "/archive/item-1/lock"
        """
        {"lock_action": "edit"}
        """

        When we spike "item-1"
        Then we get OK response
        And we get notifications
        """
        [{"event": "item:unlock", "extra": {"item": "item-1", "user": "#CONTEXT_USER_ID#"}}]
        """

        When we get "/archive/item-1"
        Then we get existing resource
        """
        {"_id": "item-1", "state": "spiked", "sign_off": "abc", "lock_user": null}
        """

    @auth
    Scenario: Spike translated item
        Given "archive"
        """
        [{"type":"text", "headline": "test1", "guid": "123", "original_creator": "abc", "state": "draft",  "language": "en-CA", "body_html": "$10"}]
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """

        When we post to "/archive/translate"
        """
        {"guid": "123", "language": "en-AU"}
        """
        And we get "/archive/#archive._id#"
        Then we get existing resource
        """
        {"translation_id": "123", "translations": ["#translate._id#"]}
        """

        When we get "/archive/#translate._id#"
        Then we get existing resource
        """
        {"type":"text", "headline": "test1", "state": "draft", "sign_off": "abc", "language": "en-AU", "body_html": "$10 (CAD 20)", "translated_from": "123", "translation_id": "123"}
        """

        When we spike "#translate._id#"
        Then we get OK response

        When we get "/archive/#translate._id#"
        Then we get existing resource
        """
        {"type":"text", "headline": "test1", "state": "spiked", "sign_off": "abc", "language": "en-AU", "body_html": "$10 (CAD 20)", "translated_from": "__none__", "translation_id": "__none__"}
        """
        When we get "/archive/#archive._id#"
        Then we get existing resource
        """
        {"translation_id": "__none__", "translations": []}
        """

    @auth
    Scenario: Spike translated item which is translated from a published item
        Given "validators"
        """
        [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
        {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{  "type":"text", "headline": "test1", "guid": "123", "original_creator": "#CONTEXT_USER_ID#",
            "state": "submitted", "source": "REUTERS", "subject":[{"qcode": "17004000", "name": "Statistics"}],
            "body_html": "Test Document body",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
        """

        When we patch "/archive/123"
        """
        {"publish_schedule":"#DATE+1#"}
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
            "name":"Channel 3","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
            "products": ["#products._id#"],
            "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
        }
        """
        And we publish "#archive._id#" with "publish" type and "published" state
        Then we get OK response
        When we post to "/archive/translate"
        """
        {"guid": "123", "language": "de"}
        """

        When we get "/archive/#translate._id#"
        Then we get existing resource
        """
        {"type":"text", "headline": "test1", "state": "submitted", "sign_off": "abc", "language": "de", "source": "AAP", 
        "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body"}
        """
        When we get "/published"
        Then we get list with 1 items
        """
        {"_items": [
            {"translation_id": "123", "translations": ["#translate._id#"]}
        ]}
        """

        When we spike "#translate._id#"
        Then we get OK response

        When we get "/archive/#translate._id#"
        Then we get existing resource
        """
        {"state": "spiked", "translation_id": "__none__", "firstcreated": "__now__"}
        """
        When we get "/published"
        Then we get list with 1 items
        """
        {"_items": [
            {"translation_id": "__none__", "translations": []}
        ]}
        """
