Feature: Authorization Server Client Management
    @auth
    Scenario: Can manage auth server clients
        # Can create a new client
        When we post to "/auth_server_clients"
        """
        [{
            "name": "Planners",
            "scope": ["EVENTS_READ", "ASSIGNMENTS_READ", "PLANNING_READ"]
        }]
        """
        Then we get OK response
        # Password is returned from POST request
        And we get existing resource
        """
        {
            "_id": "#auth_server_clients._id#",
            "password": "__any_value__",
            "name": "Planners",
            "scope": ["EVENTS_READ", "ASSIGNMENTS_READ", "PLANNING_READ"]
        }
        """

        # Passwords are not returned from GET requests
        When we get "/auth_server_clients"
        Then we get list with 1 items
        """
        {"_items": [{
            "_id": "#auth_server_clients._id#",
            "password": "__no_value__",
            "name": "Planners",
            "scope": ["EVENTS_READ", "ASSIGNMENTS_READ", "PLANNING_READ"]
        }]}
        """
        When we get "/auth_server_clients?where=name==Planners"
        Then we get list with 1 items
        """
        {"_items": [{
            "_id": "#auth_server_clients._id#",
            "password": "__no_value__",
            "name": "Planners",
            "scope": ["EVENTS_READ", "ASSIGNMENTS_READ", "PLANNING_READ"]
        }]}
        """
        When we get "/auth_server_clients/#auth_server_clients._id#"
        Then we get existing resource
        """
        {
            "_id": "#auth_server_clients._id#",
            "password": "__no_value__",
            "name": "Planners",
            "scope": ["EVENTS_READ", "ASSIGNMENTS_READ", "PLANNING_READ"]
        }
        """

        # Can delete a client
        When we delete "/auth_server_clients/#auth_server_clients._id#"
        Then we get OK response

    @auth
    Scenario: User cannot manage clients without auth_server_clients privilege
        Given "roles"
        """
        [{"name": "Editor", "privileges": {"auth_server_clients": 0}}]
        """
        And we have "Editor" role
        And we have "user" as type of user
        When we post to "/auth_server_clients"
        """
        [{
            "name": "Planners",
            "scope": ["EVENTS_READ", "ASSIGNMENTS_READ", "PLANNING_READ"]
        }]
        """
        Then we get error 403
        When we get "/auth_server_clients"
        Then we get error 403

    @auth
    Scenario: User can manage clients without auth_server_clients privilege
        Given "roles"
        """
        [{"name": "Manager", "privileges": {"auth_server_clients": 1}}]
        """
        And we have "Manager" role
        And we have "user" as type of user
        When we post to "/auth_server_clients"
        """
        [{
            "name": "Planners",
            "scope": ["EVENTS_READ", "ASSIGNMENTS_READ", "PLANNING_READ"]
        }]
        """
        Then we get OK response
        When we get "/auth_server_clients"
        Then we get list with 1 items

    @auth @wip
    Scenario: User input is validated
        When we post to "/auth_server_clients"
        """
        [{
            "name": "   ",
            "scope": ["EVENTS_READ", "ASSIGNMENTS_READ", "PLANNING_READ"]
        }]
        """
        Then we get error 400
        """
        {"_status": "ERR", "_issues": {"name": "Value is too short"}}
        """
        When we post to "/auth_server_clients"
        """
        [{
            "name": "Planners",
            "scope": []
        }]
        """
        Then we get error 400
        """
        {"_status": "ERR", "_issues": {"scope": "Value is too short"}}
        """

        When we post to "/auth_server_clients"
        """
        [{
            "name": "Planners",
            "scope": ["EVENTS_READ", "ASSIGNMENTS_READ", "PLANNING_READ"]
        }]
        """
        Then we get OK response
        When we post to "/auth_server_clients"
        """
        [{
            "name": "Planners",
            "scope": ["EVENTS_READ", "ASSIGNMENTS_READ", "PLANNING_READ"]
        }]
        """
        Then we get error 400
        """
        {"_status": "ERR", "_issues": {"name": {"unique": "Value must be unique"}}}
        """

        When we post to "/auth_server_clients"
        """
        [{
            "name": "Planners 2",
            "scope": ["EVENTS_WRITE"]
        }]
        """
        Then we get error 400
        """
        {"_status": "ERR", "_issues": {"scope": {"0": "Input should be 'ARCHIVE_READ', 'DESKS_READ', 'PLANNING_READ', 'CONTACTS_READ', 'USERS_READ', 'ASSIGNMENTS_READ' or 'EVENTS_READ'"}}}
        """
