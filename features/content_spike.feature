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
