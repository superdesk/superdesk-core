Feature: Desks

    @auth
    Scenario: Empty desks list
        Given empty "desks"
        When we get "/desks"
        Then we get list with 0 items

    @auth
    @notification
    Scenario: Create new desk
        Given empty "users"
        Given empty "desks"
        When we post to "users"
        """
        {"username": "foo", "email": "foo@bar.com", "is_active": true, "sign_off": "abc"}
        """
        Then we get existing resource
        """
        {"_id": "#users._id#", "invisible_stages": []}
        """
        When we post to "/desks"
        """
        {"name": "Sports Desk", "members": [{"user": "#users._id#"}, {"user": "#users._id#"}], "desk_language": "en"}
        """
        And we get "/desks/#desks._id#"
        Then we get existing resource
        """
        {"name": "Sports Desk", "desk_type": "authoring", "members": [{"user": "#users._id#"}], "desk_language": "en",
         "preserve_published_content": false
        }
        """
        And we get desk members count as 1
        And we get "incoming_stage"
        And we get "working_stage"
        Then we get notifications
        """
        [{"event": "desk", "extra": {"created": 1, "desk_id": "#desks._id#"}}]
        """
        When we get the default incoming stage
        And we delete latest
        Then we get error 412
        """
        {"_status": "ERR", "_message": "Cannot delete a Incoming Stage."}
        """
        When we post to "/stages"
        """
        {"name": "invisible1", "desk": "#desks._id#", "is_visible" : false}
        """
        Then we get OK response
        When we get "/users/#users._id#"
        Then we get existing resource
        """
        {"_id": "#users._id#", "invisible_stages": []}
        """
        When we get "/users/#CONTEXT_USER_ID#"
        Then we get existing resource
        """
        {"_id": "#CONTEXT_USER_ID#", "invisible_stages": ["#stages._id#"]}
        """

	@auth
    @notification
	Scenario: Update desk
	    Given empty "desks"
		When we post to "/desks"
            """
            {"name": "Sports Desk", "desk_type": "production"}
            """
        Then we get OK response
        Then we get existing resource
            """
            {"name": "Sports Desk", "desk_type": "production", "preserve_published_content": false}
            """
		When we patch latest
			 """
            {"name": "Sports Desk modified", "desk_language": "en", "preserve_published_content": true}
             """
		Then we get updated response
            """
            {"name": "Sports Desk modified", "desk_type": "production", "desk_language": "en",
            "preserve_published_content": true}
            """
        Then we get notifications
            """
            [{"event": "desk", "extra": {"updated": 1, "desk_id": "#desks._id#"}}]
            """
        When we patch latest
        """
         {"members": [{"user": "#CONTEXT_USER_ID#"}, {"user": "#CONTEXT_USER_ID#"}]}
        """
		Then we get updated response
        """
        {
            "name": "Sports Desk modified",
            "desk_type": "production",
            "desk_language": "en",
            "members": [{"user": "#CONTEXT_USER_ID#"}]
        }
        """
        And we get desk members count as 1

	@auth
    @notification
	Scenario: Delete desk
		Given "desks"
			"""
			[{"name": "test_desk1"}]
			"""
		When we post to "/desks"
        	"""
            [{"name": "test_desk2"}]
            """
        And we delete latest
        Then we get notifications
        """
        [{"event": "desk", "extra": {"deleted": 1, "desk_id": "#desks._id#"}}]
        """
        Then we get deleted response

	@auth
	Scenario: Desk name must be unique.
	    Given empty "desks"
		When we post to "/desks"
            """
            {"name": "Sports Desk"}
            """
        Then we get OK response
		When we post to "/desks"
			 """
            {"name": "sports desk"}
             """
		Then we get response code 400
		When we post to "/desks"
			 """
            {"name": "Sports Desk 2"}
             """
        Then we get OK response
		When we patch "/desks/#desks._id#"
			 """
            {"name": "SportS DesK"}
             """
		Then we get response code 400

    @auth
    Scenario: Cannot delete desk if it is assigned as a default desk to user(s)
        Given "users"
        """
        [{"username": "foo", "email": "foo@bar.com", "is_active": true}]
        """
        And "desks"
        """
        [{"name": "Sports Desk", "members": [{"user": "#users._id#"}]}]
        """
        When we patch "/users/#users._id#"
        """
        {"desk": "#desks._id#"}
        """
        And we delete "/desks/#desks._id#"
        Then we get error 412
        """
        {"_message": "Cannot delete desk as it is assigned as default desk to user(s)."}
        """

    @auth
    @notification
    Scenario: Remove user from desk membership
        Given "users"
        """
        [{"username": "foo", "email": "foo@bar.com", "is_active": true}]
        """
        And "desks"
        """
        [{"name": "Sports Desk", "members": [{"user": "#users._id#"}]}]
        """
        When we patch "/desks/#desks._id#"
        """
        { "members": []}
        """
        Then we get updated response
        Then we get notifications
        """
        [{"event": "desk_membership_revoked", "extra": {"updated": 1, "user_ids": ["#users._id#"]}}]
        """

    @auth
    Scenario: Set the monitoring settings
        Given "users"
        """
        [{"username": "foo", "email": "foo@bar.com", "is_active": true}]
        """
        And "desks"
        """
        [{"name": "Sports Desk", "members": [{"user": "#users._id#"}]}]
        """
        When we patch "/desks/#desks._id#"
        """
        { "monitoring_settings": [{"_id": "id_stage", "type": "stage", "max_items": 10},
                                  {"_id": "id_saved_search", "type": "search", "max_items": 20},
                                  {"_id": "id_personal", "type": "personal", "max_items": 15}
                                 ]
        }
        """
        Then we get updated response
        When we get "/desks"
        Then we get list with 1 items
            """
            {"_items": [{"name": "Sports Desk",
                          "monitoring_settings": [{"_id": "id_stage", "type": "stage", "max_items": 10},
                                                  {"_id": "id_saved_search", "type": "search", "max_items": 20},
                                                  {"_id": "id_personal", "type": "personal", "max_items": 15}
                                                 ]
                        }]
            }
            """

	@auth
    @notification
	Scenario: Update desk type
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
		When we patch "/desks/#desks._id#"
        """
         {"name": "Sports Desk modified", "desk_type": "production"}
        """
        Then we get OK response
		When we patch "/desks/#desks._id#"
        """
         {"name": "Sports Desk modified", "desk_type": "authoring"}
        """
        Then we get OK response
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
            "last_authoring_desk": "#SPORTS_DESK_ID#"
            }
        }
        """
        And there is no "last_production_desk" in task
		When we patch "/desks/#SPORTS_DESK_ID#"
        """
        {"name": "Sports Desk modified", "desk_type": "production"}
        """
        Then we get error 400
        """
        {"_issues": {"validator exception": "400: Cannot update Desk Type as there are article(s) referenced by the Desk."}}
        """

    @auth
    @notification
    Scenario: Simple sluglines for desk
        Given we have "desks" with "SPORTS_DESK_ID" and success
        """
        [{"name": "Sports", "desk_type": "authoring"}]
        """
        Given "published"
         """
         [{"_id":"1","slugline": "slugline1", "last_published_version": "True", "state": "published",
           "task": {"desk": "#SPORTS_DESK_ID#"}, "place": [{"name": "FED"}],
           "headline": "one", "family_id": 1},
         {"_id":"2","slugline": "slugline2", "last_published_version": "True", "state": "published",
         "task": {"desk": "#SPORTS_DESK_ID#"}, "place": [{"name": "FED"}], "headline": "two", "family_id": 2},
         {"_id":"3","slugline": "slugline3", "last_published_version": "True", "state": "published",
         "task": {"desk": "#SPORTS_DESK_ID#"}, "place": [{"name": "EUR", "group": "Rest Of World"}],
         "headline": "three", "family_id": 3}]
         """
        When we post to "users"
        """
        {"username": "foo", "email": "foo@bar.com", "is_active": true, "sign_off": "abc"}
        """
        When we get "/desks/#SPORTS_DESK_ID#/sluglines"
        Then we get existing resource
        """
            {"_items": [
                    {
                        "place": "Domestic",
                        "items": [
                            {"headline": "one", "slugline": "slugline1", "name": "Domestic", "old_sluglines": []},
                            {"headline": "two", "slugline": "slugline2", "name": "Domestic", "old_sluglines": []}
                        ]
                    },
                    {
                        "place": "EUR",
                        "items": [
                            {"headline": "three", "slugline": "slugline3", "name": "EUR", "old_sluglines": []}
                        ]
                    }
                ]
            }
        """

    @auth
    @notification
    Scenario: Simple sluglines for desk with no place
        Given we have "desks" with "SPORTS_DESK_ID" and success
        """
        [{"name": "Sports", "desk_type": "authoring"}]
        """
        Given "published"
         """
         [{"_id":"1","slugline": "slugline1", "last_published_version": "True", "state": "published",
         "task": {"desk": "#SPORTS_DESK_ID#"}, "headline": "one", "family_id": 1},
         {"_id":"2","slugline": "slugline2", "last_published_version": "True", "state": "published",
         "task": {"desk": "#SPORTS_DESK_ID#"}, "place": null, "headline": "two", "family_id": 2}]
         """
        When we post to "users"
        """
        {"username": "foo", "email": "foo@bar.com", "is_active": true, "sign_off": "abc"}
        """
        When we get "/desks/#SPORTS_DESK_ID#/sluglines"
        Then we get existing resource
        """
            {
                "_items": [
                    {
                        "place": "Domestic",
                        "items": [
                            {"headline": "one", "slugline": "slugline1", "name": "Domestic", "old_sluglines": []},
                            {"headline": "two", "slugline": "slugline2", "name": "Domestic", "old_sluglines": []}
                        ]
                    }
                ]
            }
        """

    @auth
    @notification
    Scenario: Simple change of slugline in same family
        Given we have "desks" with "SPORTS_DESK_ID" and success
        """
        [{"name": "Sports", "desk_type": "authoring"}]
        """
        When we post to "published" with delay
         """
         [{"_id":"1","slugline": "slugline1", "last_published_version": true, "state": "published",
         "task": {"desk": "#SPORTS_DESK_ID#"}, "place": [{"name": "FED"}], "headline": "one", "family_id": "1"}]
         """
        And we post to "published" with delay
         """
         [{"_id":"2","slugline": "slugline2", "last_published_version": true, "state": "published",
         "task": {"desk": "#SPORTS_DESK_ID#"}, "place": [{"name": "FED"}], "headline": "one", "family_id": "1"}]
         """
        When we post to "users"
        """
        {"username": "foo", "email": "foo@bar.com", "is_active": true, "sign_off": "abc"}
        """
        When we get "/desks/#SPORTS_DESK_ID#/sluglines"
        Then we get existing resource
        """
            {"_items":
                [
                    {
                        "place": "Domestic",
                        "items": [{"name": "Domestic", "old_sluglines": ["slugline1"], "slugline":
                                    "slugline2", "headline": "one"}]
                    }
                ]
            }
        """

    @auth
    Scenario: When creating/updating item add desk metadata
        Given "desks"
        """
        [{"desk_metadata": {"anpa_category": [{"qcode": "sport"}], "headline": "sports", "slugline": "sp"}}]
        """
        And "archive"
        """
        [{"_id": "item1", "headline": "test", "type": "text"}]
        """
        When we patch "/archive/item1"
        """
        {"task": {"desk": "#desks._id#"}, "slugline": "foo"}
        """
        Then we get updated response
        """
        {"anpa_category": [{"qcode": "sport"}], "slugline": "foo", "headline": "test"}
        """
        When we post to "/archive"
        """
        {"slugline": "x", "task": {"desk": "#desks._id#"}}
        """
        Then we get new resource
        """
        {"slugline": "x", "headline": "sports", "anpa_category": [{"qcode": "sport"}]}
        """

    @auth
    @notification
    Scenario: Retrieve number of items with desk stages overview
        Given we have "desks" with "SPORTS_DESK_ID" and success
        """
        [{"name": "Sports", "desk_type": "authoring"}]
        """
        And we have "desks" with "POLITICS_DESK_ID" and success
        """
        [{"name": "Politics", "desk_type": "authoring"}]
        """
        Given "archive"
         """
         [
         {"_id":"1","slugline": "slugline1", "state": "draft",
         "task": {"desk": "#SPORTS_DESK_ID#", "stage": "#desks.working_stage#"}, "headline": "one", "family_id": 1},
         {"_id":"2","slugline": "slugline2", "state": "draft",
         "task": {"desk": "#SPORTS_DESK_ID#", "stage": "#desks.working_stage#"}, "place": null, "headline": "two",
         "family_id": 2},
         {"_id":"3","slugline": "slugline3", "byline": "byline1", "last_published_version": "True",
         "state": "draft", "task": {"desk": "#SPORTS_DESK_ID#", "stage": "#desks.incoming_stage#"}, "place": null,
         "headline": "three", "family_id": 2},
         {"_id":"4","slugline": "slugline4", "last_published_version": "True", "state": "draft",
         "task": {"desk": "#POLITICS_DESK_ID#", "stage": "#desks.incoming_stage#"}, "place": null, "headline": "four",
         "family_id": 2},
         {"_id":"5","slugline": "slugline5", "state": "draft",
         "task": {"desk": "#POLITICS_DESK_ID#", "stage": "#desks.incoming_stage#"}, "place": null, "headline": "five",
         "family_id": 2},
         {"_id":"6","slugline": "slugline6", "state": "published",
         "task": {"desk": "#SPORTS_DESK_ID#", "stage": "#desks.incoming_stage#"}, "place": null, "headline": "six",
         "family_id": 2},
         {"_id":"7","slugline": "slugline6", "state": "killed",
         "task": {"desk": "#POLITICS_DESK_ID#", "stage": "#desks.incoming_stage#"}, "place": null, "headline": "seven",
         "family_id": 2}
         ]
         """
        When we get "/desks/#SPORTS_DESK_ID#/overview/stages"
        Then we get existing resource
        """
            {
                "_items": [
                    {
                        "stage": "#desks.incoming_stage#",
                        "count": 1
                    },
                    {
                        "stage": "#desks.working_stage#",
                        "count": 2
                    }
                ]
            }
        """
        When we get "/desks/all/overview/stages"
        Then we get existing resource
        """
            {
                "_items": [
                    {
                        "stage": "#desks.incoming_stage#",
                        "count": 3
                    },
                    {
                        "stage": "#desks.working_stage#",
                        "count": 2
                    }
                ]
            }
        """
        When we post to "/desks/all/overview/stages"
        """
            {
                "filters": {
                    "slugline": ["slugline3", "slugline4"]
                }
            }
        """
        Then we get existing resource
        """
            {
                "_items": [
                    {
                        "stage": "#desks.incoming_stage#",
                        "count": 2
                    }
                ]
            }
        """
        When we post to "/desks/#SPORTS_DESK_ID#/overview/stages"
        """
            {
                "filters": {
                    "headline": ["two"]
                }
            }
        """
        Then we get existing resource
        """
            {
                "_items": [
                    {
                        "stage": "#desks.working_stage#",
                        "count": 1
                    }
                ]
            }
        """
        When we post to "/desks/#SPORTS_DESK_ID#/overview/stages"
        """
            {
                "filters": {
                    "byline": ["byline1"]
                }
            }
        """
        Then we get existing resource
        """
            {
                "_items": [
                    {
                        "stage": "#desks.incoming_stage#",
                        "count": 1
                    }
                ]
            }
        """

    @auth
    @notification
    Scenario: Retrieve number of items with desk assignents overview
        Given we have "desks" with "SPORTS_DESK_ID" and success
        """
        [{"name": "Sports", "desk_type": "authoring"}]
        """
        And we have "desks" with "POLITICS_DESK_ID" and success
        """
        [{"name": "Politics", "desk_type": "authoring"}]
        """
        Given "assignments"
         """
         [
         {"_id":"1", "assigned_to":{"desk":"#SPORTS_DESK_ID#", "state":"assigned"}, "type":"assignment",
          "planning" : { "genre":[], "slugline":"test 1", "g2_content_type":"text" }},
         {"_id":"2", "assigned_to":{"desk":"#SPORTS_DESK_ID#", "state":"assigned"}, "type":"assignment",
          "planning" : { "genre":[], "slugline":"test 2", "g2_content_type":"text" }},
         {"_id":"3", "assigned_to":{"desk":"#SPORTS_DESK_ID#", "state":"in_progress"}, "type":"assignment",
          "planning" : { "genre":[], "slugline":"test 3", "g2_content_type":"text" }},
         {"_id":"4", "assigned_to":{"desk":"#SPORTS_DESK_ID#", "state":"in_progress"}, "type":"assignment",
          "planning" : { "genre":[], "slugline":"test 4", "g2_content_type":"text" }},
         {"_id":"5", "assigned_to":{"desk":"#SPORTS_DESK_ID#", "state":"in_progress"}, "type":"assignment",
          "planning" : { "genre":[], "slugline":"test 5", "g2_content_type":"text" }},
         {"_id":"6", "assigned_to":{"desk":"#SPORTS_DESK_ID#", "state":"in_progress"}, "type":"assignment",
          "planning" : { "genre":[], "slugline":"test 6", "g2_content_type":"text" }},
         {"_id":"7", "assigned_to":{"desk":"#SPORTS_DESK_ID#", "state":"completed"}, "type":"assignment",
          "planning" : { "genre":[], "slugline":"test 7", "g2_content_type":"text" }},
         {"_id":"8", "assigned_to":{"desk":"#POLITICS_DESK_ID#", "state":"in_progress"}, "type":"assignment",
          "planning" : { "genre":[], "slugline":"test 8", "g2_content_type":"text" }},
         {"_id":"9", "assigned_to":{"desk":"#POLITICS_DESK_ID#", "state":"completed"}, "type":"assignment",
          "planning" : { "genre":[], "slugline":"test 9", "g2_content_type":"text" }},
         {"_id":"10", "assigned_to":{"desk":"#POLITICS_DESK_ID#", "state":"completed"}, "type":"assignment",
          "planning" : { "genre":[], "slugline":"test 10", "g2_content_type":"text" }}
         ]
         """
        When we get "/desks/#SPORTS_DESK_ID#/overview/assignments"
        Then we get existing resource
        """
            {
                "_items": [
                    {
                        "state": "assigned",
                        "count": 2
                    },
                    {
                        "state": "in_progress",
                        "count": 4
                    },
                    {
                        "state": "completed",
                        "count": 1
                    }
                ]
            }
        """
        When we get "/desks/all/overview/assignments"
        Then we get existing resource
        """
            {
                "_items": [
                    {
                        "state": "assigned",
                        "count": 2
                    },
                    {
                        "state": "in_progress",
                        "count": 5
                    },
                    {
                        "state": "completed",
                        "count": 3
                    }
                ]
            }
        """

    @auth
    @notification
    Scenario: Retrieve overview of users
        Given we have "roles" with "ROLE_EDITOR_ID" and success
        """
        [{"name": "Editor"}]
        """
        And we have "roles" with "ROLE_SUBEDITOR_ID" and success
        """
        [{"name": "Sub Editor"}]
        """
        And we have "roles" with "ROLE_JOURNALIST_ID" and success
        """
        [{"name": "Journalist"}]
        """
        Given we have "users" with "USER_1_ID" and success
        """
        {"username": "user_1", "email": "user_1@example.net", "is_active": true, "role": "#ROLE_JOURNALIST_ID#"}
        """
        And we have "users" with "USER_2_ID" and success
        """
        {"username": "user_2", "email": "user_2@example.net", "is_active": true, "role": "#ROLE_JOURNALIST_ID#"}
        """
        And we have "users" with "USER_3_ID" and success
        """
        {"username": "user_3", "email": "user_3@example.net", "is_active": true, "role": "#ROLE_EDITOR_ID#"}
        """
        And we have "users" with "USER_4_ID" and success
        """
        {"username": "user_4", "email": "user_4@example.net", "is_active": true, "role": "#ROLE_SUBEDITOR_ID#"}
        """
        And we have "users" with "USER_5_ID" and success
		# This user has no associated article on purpose (cf. SDESK-5557)
        # she must associated to a desk to test the issue (she is associated to Sports desk below)
        """
        {"username": "user_5", "email": "user_5@example.net", "is_active": true, "role": "#ROLE_SUBEDITOR_ID#"}
        """
        Given we have "desks" with "SPORTS_DESK_ID" and success
        """
        [{"name": "Sports", "desk_type": "authoring", "members": [{"user": "#USER_1_ID#"},
          {"user": "#USER_2_ID#"}, {"user": "#USER_3_ID#"}, {"user": "#USER_5_ID#"}] }]
        """
        And we have "desks" with "POLITICS_DESK_ID" and success
        """
        [{"name": "Politics", "desk_type": "authoring", "members": [{"user": "#USER_1_ID#"},
          {"user": "#USER_3_ID#"}, {"user": "#USER_4_ID#"}] }]
        """
        Given "archive"
         """
         [
         {"_id":"1","slugline": "slugline1", "state": "in_progress", "original_creator": "#USER_1_ID#",
         "task": {"desk": "#SPORTS_DESK_ID#", "stage": "#desks.working_stage#"}, "headline": "one", "family_id": 1,
         "assignment_id": "123", "lock_user": "#USER_3_ID#"},
         {"_id":"2","slugline": "slugline2", "state": "in_progress", "original_creator": "#USER_2_ID#",
         "task": {"desk": "#SPORTS_DESK_ID#", "stage": "#desks.working_stage#"}, "place": null, "headline": "two",
         "family_id": 2, "assignment_id": "456", "lock_user": "#USER_4_ID#"},
         {"_id":"3","slugline": "slugline3", "last_published_version": "True", "state": "published",
         "task": {"desk": "#SPORTS_DESK_ID#", "stage": "#desks.incoming_stage#"}, "place": null, "headline": "three",
         "family_id": 2, "original_creator": "#USER_3_ID#"},
         {"_id":"4","slugline": "slugline4", "last_published_version": "True", "state": "published",
         "task": {"desk": "#POLITICS_DESK_ID#", "stage": "#desks.incoming_stage#"}, "place": null, "headline": "four",
         "family_id": 2, "original_creator": "#USER_4_ID#", "lock_user": "#USER_3_ID#"},
         {"_id":"5","slugline": "slugline5", "state": "in_progress",
         "task": {"desk": "#SPORTS_DESK_ID#", "stage": "#desks.incoming_stage#"}, "place": null, "headline": "five",
         "family_id": 2, "original_creator": "#USER_1_ID#", "assignment_id": "789"},
         {"_id":"6","slugline": "slugline6", "state": "in_progress",
         "task": {"desk": "#SPORTS_DESK_ID#", "stage": "#desks.incoming_stage#"}, "place": null, "headline": "five",
         "family_id": 2, "original_creator": "#USER_2_ID#", "lock_user": "#USER_3_ID#"}
         ]
         """
        # we can't check assignments because adding json to "assignments" requires planning to be installed
        When we get "/desks/#SPORTS_DESK_ID#/overview/users"
        Then we get existing resource
        """
            {
              "_items": [
                {
                  "authors": {
                    "#USER_1_ID#": {
                      "assigned": 0,
                      "locked": 0
                    },
                    "#USER_2_ID#": {
                      "assigned": 0,
                      "locked": 0
                    }
                  },
                  "role": "#ROLE_JOURNALIST_ID#"
                },
                {
                  "authors": {
                    "#USER_3_ID#": {
                      "assigned": 0,
                      "locked": 2
                    }
                  },
                  "role": "#ROLE_EDITOR_ID#"
                }
              ]
            }
        """
        When we get "/desks/all/overview/users"
        Then we get existing resource
        """
            {
                "_items": [
                  {
                    "authors": {
                      "#USER_3_ID#": {
                        "assigned": 0,
                        "locked": 2
                      }
                    },
                    "role": "#ROLE_EDITOR_ID#"
                  },
                  {
                    "authors": {
                      "#USER_4_ID#": {
                        "assigned": 0,
                        "locked": 1
                      }
                    },
                    "role": "#ROLE_SUBEDITOR_ID#"
                  },
                  {
                    "authors": {
                      "#USER_1_ID#": {
                        "assigned": 0,
                        "locked": 0
                      },
                      "#USER_2_ID#": {
                        "assigned": 0,
                        "locked": 0
                      }
                    },
                    "role": "#ROLE_JOURNALIST_ID#"
                  }
                ]
            }
        """

    @auth
    @notification
    Scenario: Make the desk available in default content template
        Given empty "desks"
        Given "content_templates"
        """
        [{
            "template_name": "test",
            "template_type": "create",
            "data": {"headline": "test", "type": "text", "slugline": "test"}
        }]
        """
        When we post to "/desks"
        """
        {
            "name": "Sports Desk",
            "desk_language": "en",
            "default_content_template": "#content_templates._id#"
        }
        """
        Then we get OK response
        When we get "content_templates/#content_templates._id#"
        Then we get existing resource
        """
        {
            "template_name": "test",
            "template_type": "create",
            "template_desks": ["#desks._id#"]
        }
        """
        
