Feature: Config

    @auth
    Scenario: Non-existing config return None
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
