Feature: Client Config

    Scenario: Read client config
        When we get "client_config"
        Then we get existing resource
        """
        {
            "config": {
                "xmpp_auth": false
            }
        }
        """
