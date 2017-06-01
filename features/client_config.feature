Feature: Client Config

    Scenario: Read client config
        When we get "client_config"
        Then we get existing resource
        """
        {
            "config": {
                "no_takes": false,
                "xmpp_auth": false,
                "google_auth": false
            }
        }
        """
