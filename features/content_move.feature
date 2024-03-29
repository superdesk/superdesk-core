Feature: Move or Send Content to another desk

    @auth
    @notification
    Scenario: Send Content from personal to another desk
        Given "desks"
        """
        [{"name": "Sports", "desk_type": "production"}]
        """
        And "archive"
        """
        [{"guid": "123", "type":"text", "headline": "test1", "guid": "123", "state": "draft", "task": {"user": "#CONTEXT_USER_ID#"}, "versioncreated": "2020-01-01T10:00:00+0000"}]
        """
        When we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        And we save etag
        And we get notifications
        """
        [
            {
                "event": "item:move",
                "extra": {
                    "item": "123",
                    "to_desk": "#desks._id#",
                    "to_stage": "#desks.incoming_stage#"
                }
            }
        ]
        """
        When we get "/archive/123?version=all"
        Then we get list with 1 items
        When we get "/archive/123"
        Then we get existing resource
        """
        { "headline": "test1", "guid": "123", "state": "submitted", "_current_version": 1,
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
          "versioncreated": "__now__"
        }
        """
        Then there is no "last_production_desk" in task
        And there is no "last_authoring_desk" in task
        And we get matching etag

    @auth
    @notification
    Scenario: Send Content from one desk to another desk and validate metadata set by API
        Given we have "desks" with "SPORTS_DESK_ID" and success
        """
        [{"name": "Sports", "desk_type": "authoring"}]
        """
        When we post to "archive"
        """
        [{  "type":"text", "headline": "test1", "guid": "123", "state": "submitted",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
        """
        And we get "/archive/123"
        Then we get existing resource
        """
        {"headline": "test1", "sign_off": "abc"}
        """
        When we post to "/desks" with "FINANCE_DESK_ID" and success
        """
        [{"name": "Finance", "desk_type": "production" }]
        """
        And we switch user
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        And we get notifications
        """
        [
            {
                "event": "item:move",
                "extra": {
                    "item": "123",
                    "from_desk": "#SPORTS_DESK_ID#",
                    "to_desk": "#desks._id#",
                    "to_stage": "#desks.incoming_stage#"
                }
            }
        ]
        """
        When we get "/archive/123"
        Then we get existing resource
        """
        { "operation": "move", "headline": "test1", "guid": "123", "state": "submitted", "_current_version": 2, "sign_off": "abc/foo",
          "task": {
            "desk": "#desks._id#",
            "stage": "#desks.incoming_stage#",
            "last_authoring_desk": "#SPORTS_DESK_ID#",
            "last_desk": "#SPORTS_DESK_ID#",
            "desk_history": ["#SPORTS_DESK_ID#"]
            }
        }
        """
        And there is no "last_production_desk" in task

    @auth
    Scenario: Send Content from one desk to another desk with same desk_type does not change the last_production_desk and last_authoring_desk
        Given we have "desks" with "SPORTS_DESK_ID" and success
        """
        [{"name": "Sports", "desk_type": "authoring"}]
        """
        When we post to "archive"
        """
        [{  "type":"text", "headline": "test1", "guid": "123", "state": "submitted",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
        """
        And we get "/archive/123"
        Then we get existing resource
        """
        {"headline": "test1", "sign_off": "abc"}
        """
        When we post to "/desks" with "FINANCE_DESK_ID" and success
        """
        [{"name": "Finance", "desk_type": "production" }]
        """
        And we switch user
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we get "/archive/123"
        Then we get existing resource
        """
        { "operation": "move", "headline": "test1", "guid": "123", "state": "submitted", "_current_version": 2, "sign_off": "abc/foo",
          "task": {
            "desk": "#desks._id#",
            "stage": "#desks.incoming_stage#",
            "last_authoring_desk": "#SPORTS_DESK_ID#",
            "last_desk": "#SPORTS_DESK_ID#",
            "desk_history": ["#SPORTS_DESK_ID#"]
            }
        }
        """
        And there is no "last_production_desk" in task
        When we post to "/desks" with "NATIONAL_DESK_ID" and success
        """
        [{"name": "National", "desk_type": "production" }]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we get "/archive/123"
        Then we get existing resource
        """
        { "operation": "move", "headline": "test1", "guid": "123", "state": "submitted", "_current_version": 3, "sign_off": "abc/foo",
          "task": {
            "desk": "#desks._id#",
            "stage": "#desks.incoming_stage#",
            "last_authoring_desk": "#SPORTS_DESK_ID#",
            "last_desk": "#FINANCE_DESK_ID#",
            "desk_history": ["#SPORTS_DESK_ID#", "#FINANCE_DESK_ID#"]
            }
        }
        """
        And there is no "last_production_desk" in task
        When we post to "/desks" with "ENTERTAINMENT_DESK_ID" and success
        """
        [{"name": "Entertainment", "desk_type": "authoring" }]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get OK response
        When we get "/archive/123"
        Then we get existing resource
        """
        { "operation": "move", "headline": "test1", "guid": "123", "state": "submitted", "_current_version": 4, "sign_off": "abc/foo",
          "task": {
            "desk": "#desks._id#",
            "stage": "#desks.incoming_stage#",
            "last_production_desk": "#NATIONAL_DESK_ID#",
            "last_authoring_desk": "#SPORTS_DESK_ID#",
            "last_desk": "#NATIONAL_DESK_ID#",
            "desk_history": ["#SPORTS_DESK_ID#", "#FINANCE_DESK_ID#", "#NATIONAL_DESK_ID#"]
            }
        }
        """


    @auth
    Scenario: Send Content from one stage to another stage with same desk
        Given "desks"
        """
        [{"name": "Sports", "desk_type": "production"}]
        """
        When we post to "archive"
        """
        [{  "type":"text", "headline": "test1", "guid": "123", "state": "submitted",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
        """
        And we post to "/stages"
        """
        [
          {
          "name": "another stage",
          "description": "another stage",
          "task_status": "in_progress",
          "desk": "#desks._id#"
          }
        ]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#stages._id#"}}]
        """
        Then we get OK response
        When we get "/archive/123"
        Then we get existing resource
        """
        { "headline": "test1", "guid": "123", "state": "submitted", "_current_version": 2,
          "task": {"desk": "#desks._id#", "stage": "#stages._id#", "user": "#CONTEXT_USER_ID#"}}
        """
        And there is no "last_authoring_desk" in task
        And there is no "last_production_desk" in task


    @auth
    @clean
    Scenario: Send Content from one stage to another stage with incoming validation rule fails
        Given "desks"
        """
        [{"name": "Politics"}]
        """
        Given we create a new macro "validate_headline_macro.py"
        When we post to "archive"
        """
        [{  "type":"text", "guid": "123", "state": "submitted",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
        """
        And we post to "/stages"
        """
        [
          {
          "name": "another stage",
          "description": "another stage",
          "task_status": "in_progress",
          "desk": "#desks._id#",
          "incoming_macro": "validate_headline"
          }
        ]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#stages._id#"}}]
        """
        Then we get error 400
        """
        {"_message": "Error:'Headline cannot be empty!' in incoming rule:Validate Headline for stage:another stage"}
        """

    @auth
    @clean
    Scenario: Send Content from one stage to another stage with incoming rule succeeds
        Given "desks"
        """
        [{"name": "Politics"}]
        """
        Given we create a new macro "behave_macro.py"
        When we post to "archive"
        """
        [{  "type":"text", "guid": "123", "state": "submitted",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
        """
        And we post to "/stages"
        """
        [
          {
          "name": "another stage",
          "description": "another stage",
          "task_status": "in_progress",
          "desk": "#desks._id#",
          "incoming_macro": "update_fields"
          }
        ]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#stages._id#"}}]
        """
        Then we get OK response
        When we get "/archive/123"
        Then we get existing resource
        """
        { "guid": "123", "state": "submitted", "_current_version": 2,
          "abstract": "Abstract has been updated",
          "task": {"desk": "#desks._id#", "stage": "#stages._id#", "user": "#CONTEXT_USER_ID#"}}
        """

    @auth
    @clean
    Scenario: Send Content from one stage to another stage with outgoing validation rule fails
        Given "desks"
        """
        [{"name": "Politics"}]
        """
        Given we create a new macro "validate_headline_macro.py"
        When we get "/stages/#desks.incoming_stage#"
        When we patch "/stages/#desks.incoming_stage#"
        """
        {
          "outgoing_macro": "validate_headline"
        }
        """
        When we post to "archive"
        """
        [{  "type":"text", "guid": "123", "state": "submitted",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
        """
        And we post to "/stages"
        """
        [
          {
          "name": "another stage",
          "description": "another stage",
          "task_status": "in_progress",
          "desk": "#desks._id#"
          }
        ]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#stages._id#"}}]
        """
        Then we get error 400
        """
        {"_message": "Error:'Headline cannot be empty!' in outgoing rule:Validate Headline for stage:Incoming Stage"}
        """

    @auth
    @clean
    Scenario: Send Content from one stage to another stage with outgoing rule succeeds
        Given "desks"
        """
        [{"name": "Politics"}]
        """
        Given we create a new macro "behave_macro.py"
        When we get "/stages/#desks.incoming_stage#"
        When we patch "/stages/#desks.incoming_stage#"
        """
        {
          "outgoing_macro": "update_fields"
        }
        """
        When we post to "archive"
        """
        [{  "type":"text", "guid": "123", "state": "submitted",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
        """
        And we post to "/stages"
        """
        [
          {
          "name": "another stage",
          "description": "another stage",
          "task_status": "in_progress",
          "desk": "#desks._id#"
          }
        ]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#stages._id#"}}]
        """
        Then we get OK response
        When we get "/archive/123"
        Then we get existing resource
        """
        { "guid": "123", "state": "submitted", "_current_version": 2,
          "abstract": "Abstract has been updated",
          "task": {"desk": "#desks._id#", "stage": "#stages._id#", "user": "#CONTEXT_USER_ID#"}}
        """

    @auth
    Scenario: Move should fail if no desk is specified
        Given "archive"
        """
        [{  "type":"text", "headline": "test1", "guid": "123", "original_creator": "abc", "state": "submitted",
            "task": {"user": "#CONTEXT_USER_ID#"}}]
        """
        When we post to "/archive/123/move"
        """
        [{"task": {}}]
        """
        Then we get error 400
        """
        {"_issues": {"task": {"stage": {"required": 1}, "desk": {"required": 1}}}}
        """

    @auth
    Scenario: Move should fail if desk and no stage is specified
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{  "type":"text", "headline": "test1", "guid": "123", "original_creator": "abc", "state": "submitted",
            "task": {"user": "#CONTEXT_USER_ID#"}}]
        """
        When we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#"}}]
        """
        Then we get error 400
        """
        {"_issues": {"task": {"stage": {"required": 1}}}}
        """

    @auth
    Scenario: Move should fail if desk and stage are same
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{  "type":"text", "headline": "test1", "guid": "123", "original_creator": "abc", "state": "submitted",
            "task": {"desk":"#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
        """
        When we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get error 412
        """
        {"_message":"Move is not allowed within the same stage.", "_status": "ERR"}
        """

    @auth
    Scenario: Move should fail if user trying to move a published content
        Given "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{  "type":"text", "headline": "test1", "guid": "123", "original_creator": "abc", "state": "published",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
        """
        When we post to "/desks"
        """
        [{"name": "Finance"}]
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get response code 201

    @auth
    Scenario: User can move content without a move privilege if member of the destination desk
        Given "users"
        """
        [{"username": "foo", "password": "bar", "email": "foo@bar.com"}]
        """
        And "desks"
        """
        [{"name": "Sports"}]
        """
        And "archive"
        """
        [{  "type":"text", "headline": "test1", "guid": "123", "original_creator": "abc", "state": "submitted",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#users._id#"}}]
        """
        When we patch "/users/#users._id#"
        """
        {"user_type": "user", "privileges": {"archive": 1, "move": 0}}
        """
        When we post to "/desks"
        """
        [{"name": "Finance", "members": [{"user": "#users._id#"}]}]
        """
        And we login as user "foo" with password "bar" and user type "user"
        """
        {"user_type": "user", "email": "foo.bar@foobar.org"}
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get response code 201


    @auth
    Scenario: User can't move content without a move privilege if not member of the destination desk
        Given "users"
        """
        [{"username": "foo", "password": "bar", "email": "foo@bar.com"}]
        """
        And "desks"
        """
        [{"name": "Sports", "members": [{"user": "#users._id#"}]}]
        """
        And "archive"
        """
        [{  "type":"text", "headline": "test1", "guid": "123", "original_creator": "abc", "state": "submitted",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#users._id#"}}]
        """
        When we patch "/users/#users._id#"
        """
        {"user_type": "user", "privileges": {"archive": 1, "move": 0}}
        """
        When we post to "/desks"
        """
        [{"name": "Finance"}]
        """
        And we login as user "foo" with password "bar" and user type "user"
        """
        {"user_type": "user", "email": "foo.bar@foobar.org"}
        """
        And we post to "/archive/123/move"
        """
        [{"task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get response code 403


	@auth
    Scenario: Move package with all package
        Given empty "archive"
        And "desks"
        """
        [{"name": "source desk"}]
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
        When we post to "/desks"
        """
        [{"_id": ObjectId("123456789"), "name": "destination desk"}]
        """
        And we post to "/archive/package-1/move"
        """
        [{"allPackageItems": true, "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]
        """
        Then we get response code 201

        When we get "/archive/package-1"
        Then we get existing resource
        """
        {"_id": "package-1", "task": {"desk": "#desks._id#", "user": "#user._id#"}}
        """

        When we get "/archive/item-1"
        Then we get existing resource
        """
        { "headline": "test", "_id": "item-1", "guid": "item-1", "slugline": "WORMS",
          "task": {"desk": "#desks._id#", "user": "#user._id#"}}
        """

    @auth
    Scenario: Send Content from one desk to Personal desk
        Given we have "desks" with "SPORTS_DESK_ID" and success
        """
        [{"name": "Sports", "desk_type": "authoring"}]
        """
        When we post to "archive"
        """
        [{  "type":"text", "headline": "test1", "guid": "123", "state": "submitted",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
        """
        And we get "/archive/123"
        Then we get existing resource
        """
        {"headline": "test1", "sign_off": "abc"}
        """
        When we post to "/desks" with "FINANCE_DESK_ID" and success
        """
        [{"name": "Finance", "desk_type": "production" }]
        """
        And we switch user
        And we post to "/archive/123/move"
        """
        [{}]
        """
        Then we get OK response

        When we get "/archive/123"
        Then we get existing resource
        """
        { "operation": "move", "headline": "test1", "guid": "123", "state": "submitted", "_current_version": 2, "sign_off": "abc/foo",
          "task": {
                "user": "#CONTEXT_USER_ID#"
            }
        }
        """
