Feature: System info api

    Scenario: Health check
        When we get "/system/health"
        Then we get existing resource
        """
        {
            "application_name": "Superdesk",
            "status": "green",
            "elastic": "green",
            "mongo": "green",
            "celery": "green",
            "redis": "green"
        }
        """
 