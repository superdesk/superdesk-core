Feature: Backend meta info

    @auth
    Scenario: Fetch backend meta
        When we get "/backend_meta"
        Then we get existing resource
        """
        {}
        """
