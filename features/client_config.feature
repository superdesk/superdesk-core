Feature: Client Config

    Scenario: Read client config
        When we get "client_config"
        Then we get existing resource
        """
        {
            "config": {
                "xmpp_auth": false,
                "attachments_max_files": 10,
                "attachments_max_size": 8388608,
                "japanese_characters_per_minute": 600,
                "schema": {},
                "editor": {},
                "publish_content_expiry_minutes": 0,
                "workflow_allow_multiple_updates": false
            }
        }
        """
