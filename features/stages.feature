Feature: Stages

    Background: Setup data required to test Stages feature
        Given empty "stages"
        And "desks"
        """
        [{"name": "test_desk"}]
        """

    @auth @notification
    Scenario: Add a Stage and verify its order
        When we post to "/stages"
        """
        {"name": "show my content", "description": "Show content items created by the current logged user", "desk": "#desks._id#"}
        """
        Then we get notifications
        """
        [{"event": "stage", "extra": {"created": 1, "desk_id": "#desks._id#", "stage_id": "#stages._id#", "is_visible": true}}]
        """
        Then we get new resource
        """
        {"name": "show my content", "description": "Show content items created by the current logged user", "desk": "#desks._id#", "desk_order": 3}
        """

    @auth @notification
    Scenario: Stage name must be unique
        When we post to "/stages"
        """
        {"name": "new", "description": "Show content items created by the current logged user", "desk": "#desks._id#"}
        """
        Then we get OK response
        When we post to "/stages"
        """
        {"name": "new", "description": "Show content items created by the current logged user", "desk": "#desks._id#"}
        """
        Then we get error 400
        """
        {"_issues": {"name": {"unique": 1}}}
        """

    @auth @notification
    Scenario: Fails to add a Stage without a name
        When we post to "/stages"
        """
        {"description": "Show content items created by the current logged user"}
        """
        Then we get error 400
        """
        {"_issues": {"name": {"required": 1}, "desk": {"required": 1}}}
        """

    @auth @notification
    Scenario: Update Stage Name and Description
        When we post to "/stages"
        """
        {"name": "show my content", "description": "Show content items created by the current logged user", "desk": "#desks._id#"}
        """
        Then we get new resource
        """
        {
            "name": "show my content",
            "description": "Show content items created by the current logged user",
            "desk": "#desks._id#",
            "local_readonly": false
        }
        """
        When we patch latest
        """
        {"name": "My stage", "description": "Show content that I just updated", "local_readonly": true}
        """
        Then we get updated response
        """
        {"name": "My stage", "description": "Show content that I just updated", "desk": "#desks._id#", "local_readonly": true}
        """

    @auth @notification
    Scenario: Adding content to a stage having 0 expiry will get global expiry for the content
        When we post to "/stages"
        """
        {"name": "update expiry", "desk": "#desks._id#", "content_expiry": 0}
        """
        And we post to "/archive"
        """
        [{"_id": "testid1", "guid": "testid1", "task": {"desk": "#desks._id#", "stage" :"#stages._id#"}}]
        """
        And we get "archive/testid1"
        Then we get global content expiry

    @auth @notification
    Scenario: Adding content to a stage having -1 expiry will get global expiry for the content
        When we post to "/stages"
        """
        {"name": "update expiry", "desk": "#desks._id#", "content_expiry": -1}
        """
        And we post to "/archive"
        """
        [{"_id": "testid1", "guid": "testid1", "task": {"desk": "#desks._id#", "stage" :"#stages._id#"}}]
        """
        And we get "archive/testid1"
        Then we get global content expiry

    @auth @notification
    Scenario: Can delete an empty stage
        When we post to "/stages"
        """
        {"name": "show my content", "desk": "#desks._id#"}
        """
        And we delete "/stages/#stages._id#"
        Then we get response code 204
        Then we get notifications
        """
        [{"event": "stage", "extra": {"deleted": 1}}]
        """

    @auth @notification
    Scenario: Toggle stage invisibility for notification
        When we post to "/stages"
        """
        {"name": "stage visibility", "desk": "#desks._id#", "is_visible" : true}
        """
        And we reset notifications
        And we get "/users/#CONTEXT_USER_ID#"
        Then we get existing resource
        """
        {"_id": "#CONTEXT_USER_ID#", "invisible_stages": []}
        """
        When we patch "/stages/#stages._id#"
        """
        {"is_visible" : false}
        """
        Then we get response code 200
        When we get "/users/#CONTEXT_USER_ID#"
        Then we get existing resource
        """
        {"_id": "#CONTEXT_USER_ID#", "invisible_stages": ["#stages._id#"]}
        """
        And we get notifications
        """
        [{"event": "stage_visibility_updated", "extra": {"updated": 1, "desk_id": "#desks._id#", "stage_id": "#stages._id#", "is_visible": false}}]
        """
        When we post to "/users"
        """
        {"username": "foo", "email": "foo@bar.com", "is_active": true, "sign_off": "abc"}
        """
        Then we get OK response
        And we get existing resource
        """
        {"_id": "#users._id#", "invisible_stages": ["#stages._id#"]}
        """
        When we patch "/stages/#stages._id#"
        """
        {"is_visible" : true}
        """
        Then we get response code 200
        When we get "/users/#CONTEXT_USER_ID#"
        Then we get existing resource
        """
        {"_id": "#CONTEXT_USER_ID#", "invisible_stages": []}
        """
        When we get "/users/#users._id#"
        Then we get existing resource
        """
        {"_id": "#users._id#", "invisible_stages": []}
        """


    @auth @notification
    Scenario: Get visible and invisible stages
        When we post to "/stages"
        """
        [{"name": "invisible1", "desk": "#desks._id#", "is_visible" : false},
         {"name": "invisible2", "desk": "#desks._id#", "is_visible" : false}]
        """
        Then we get 2 visible stages
        And we get 2 invisible stages

    @auth @notification
    Scenario: Cannot delete stage if there are documents irrespective of their status
        When we post to "/stages"
        """
        {"name": "show my content", "desk": "#desks._id#"}
        """
        And we post to "archive"
        """
        [{"_id": "item-1", "slugline": "first task", "type": "text", "task": {"desk":"#desks._id#", "stage" :"#stages._id#"}}]
        """
        When we delete "/stages/#stages._id#"
        Then we get error 412
        """
        {"_status": "ERR", "_message": "Cannot delete stage as it has article(s) or referenced by versions of the article(s)."}
        """
        When we spike "item-1"
        Then we get OK response
        When we delete "/stages/#stages._id#"
        Then we get error 412
        """
        {"_status": "ERR", "_message": "Cannot delete stage as it has article(s) or referenced by versions of the article(s)."}
        """

    @auth @vocabulary @notification
    Scenario: Cannot delete stage if it is referred to by a routing scheme
        Given we have "/filter_conditions" with "FCOND_ID" and success
        """
        [{"name": "Sports Content", "field": "subject", "operator": "in", "value": "04000000"}]
        """
        And we have "/content_filters" with "FILTER_ID" and success
        """
        [{"name": "Sports Content", "content_filter": [{"expression": {"fc": ["#FCOND_ID#"]}}]}]
        """
        When we post to "/stages"
        """
        {"name": "show my content", "desk": "#desks._id#"}
        """
        And we post to "/routing_schemes"
        """
        [{"name": "routing rule scheme 1", "rules": [{
            "name": "Sports Rule", "handler": "desk_fetch_publish", "filter": "#FILTER_ID#",
            "actions": {"fetch": [{"desk": "#desks._id#", "stage": "#stages._id#", "macro": "transform"}]}
        }]}]
        """
        And we delete "/stages/#stages._id#"
        Then we get error 412
        """
        {"_status": "ERR", "_message": "Stage is referred by Ingest Routing Schemes : routing rule scheme 1"}
        """

    @auth @notification
    Scenario: Cannot delete either Working or Incoming Stage
        When we delete "/stages/#desks.working_stage#"
        Then we get error 412
        """
        {"_status": "ERR", "_message": "Cannot delete a Working Stage."}
        """
        When we delete "/stages/#desks.incoming_stage#"
        Then we get error 412
        """
        {"_status": "ERR", "_message": "Cannot delete a Incoming Stage."}
        """

    @auth
    Scenario: Content can not be created on readonly stage
        When we post to "/stages"
        """
        {"name": "show my content", "desk": "#desks._id#", "local_readonly": true}
        """
        And we post to "/archive"
        """
        {"_id": "item-1", "slugline": "first task", "type": "text", "task": {"desk":"#desks._id#", "stage" :"#stages._id#"}}
        """
        Then we get error 403
        """
        {"error": {"readonly": true}}
        """

    @auth
    Scenario: Content can be fetched to readonly stage
        When we post to "/stages"
        """
        {"name": "show my content", "desk": "#desks._id#", "local_readonly": true}
        """
        And we post to "/archive"
        """
        {"_id": "item-1", "slugline": "first task", "type": "text", "task": {"desk":"#desks._id#", "stage" :"#stages._id#"},
         "ingest_id": "foo"}
        """
        Then we get new resource

    @auth
    Scenario: Content can not be send to readonly stage
    When we post to "/stages"
        """
        {"name": "show my content", "desk": "#desks._id#", "local_readonly": true}
        """
        And we post to "/archive"
        """
        {"_id": "item-1", "slugline": "first task", "type": "text"}
        """
        Then we get new resource
        When we patch "/archive/item-1"
        """
        {"task": {"desk":"#desks._id#", "stage" :"#stages._id#"}}
        """
        Then we get error 403

    @auth
    Scenario: Content on readonly stage is not editable
        When we post to "/stages"
        """
        {"name": "show my content", "desk": "#desks._id#", "local_readonly": false}
        """
        And we post to "archive"
        """
        [{"_id": "item-1", "slugline": "first task", "type": "text", "task": {"desk":"#desks._id#", "stage" :"#stages._id#"}}]
        """
        When we patch "/stages/#stages._id#"
        """
        {"local_readonly": true}
        """
        And we patch "/archive/item-1"
        """
        {"headline": "foo"}
        """
        Then we get error 403
        """
        {"error": {"readonly": true}}
        """

    @auth
    Scenario: Reordering of stages
        Given "desks"
        """
        [
            {"name": "sports"}
        ]
        """
        Given "stages"
        """
        [
            {"_id": "first", "desk": "#desks._id#", "name": "first", "order": 1},
            {"_id": "second", "desk": "#desks._id#", "name": "second", "order": 2},
            {"_id": "third", "desk": "#desks._id#", "name": "third", "order": 3}
        ]
        """
        When we get "stages"
        Then we get ordered list with 3 items
        """
        {"_items": [
            {"_id": "first"},
            {"_id": "second"},
            {"_id": "third"}
        ]}
        """
        When we post to "stages_order"
        """
        {
            "desk": "#desks._id#",
            "stages": [
                "second",
                "third",
                "first"
            ]
        }
        """
        Then we get OK response
        When we get "stages"
        Then we get ordered list with 3 items
        """
        {"_items": [
            {"_id": "second"},
            {"_id": "third"},
            {"_id": "first"}
        ]}
        """
        When we post to "stages"
        """
        {"name": "new", "desk": "#desks._id#"}
        """
        Then we get ok response
        When we get "stages"
        Then we get ordered list with 4 items
        """
        {"_items": [
            {"_id": "second"},
            {"_id": "third"},
            {"_id": "first"},
            {"_id": "#stages._id#"}
        ]}
        """