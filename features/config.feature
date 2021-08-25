Feature: Config

    @auth
    Scenario: Non-existing config return None
        When we get "/config/foo"
        Then we get existing resource
        """
        {"_id": "foo", "val": null}
        """

    Scenario: Read config without auth
        When we get "/config/foo"
        Then we get existing resource
        """
        {"_id": "foo", "val": null}
        """

    @auth
    Scenario: Get config
        Given "config"
        """
        [{"_id": "foo", "val": {"bar": 1}}]
        """
        When we get "/config/foo"
        Then we get existing resource
        """
        {"val": {"bar": 1}}
        """

    @auth
    Scenario: Set config
        When we post to "/config"
        """
        {"_id": "foo", "val": {"bar": 1}}
        """
        Then we get new resource
        When we get "/config/foo"
        Then we get existing resource
        """
        {"_id": "foo", "val": {"bar": 1}}
        """
        When we post to "/config"
        """
        {"_id": "foo", "val": {"bar": 2}}
        """
        Then we get new resource
        When we get "/config/foo"
        Then we get existing resource
        """
        {"_id": "foo", "val": {"bar": 2}}
        """

    @auth
    Scenario: Default values
        When we get "/config/client-settings"
        Then we get existing resource
        """
        {
            "_id": "client-settings",
            "val": {
                "defaultRoute": "/workspace",
                "auth": {"google": false}
            }
        }
        """
        When we post to "/config"
        """
        {
            "_id": "client-settings",
            "val": {
                "auth.google": true
            }
        }
        """
        And we get "/config/client-settings"
        Then we get existing resource
        """
        {
            "_id": "client-settings",
            "val": {
                "defaultRoute": "/workspace",
                "auth": {"google": true}
            }
        }
        """
        When we post to "/config"
        """
        {
            "_id": "client-settings",
            "val": {
                "defaultRoute": "/settings"
            }
        }
        """
        And we get "/config/client-settings"
        Then we get existing resource
        """
        {
            "_id": "client-settings",
            "val": {
                "defaultRoute": "/settings",
                "auth": {"google": true}
            }
        }
        """
