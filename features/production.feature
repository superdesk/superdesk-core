Feature: News Items Production

    @auth
    Scenario: Can display all items no matter what's the status
        When we post to "archive"
        """
        [
            {"guid": "in_progress", "version": 1, "state": "in_progress"},
            {"guid": "published", "version": 1, "state": "published"}
        ]
        """
        And we get "/production"
        Then we get list with 2 items
        """
        {
            "_items": [
                {
                    "guid": "in_progress",
                    "_links": {"self": {"title": "Archive", "href": "/archive/in_progress"}}
                },
                {
                    "guid": "published"
                }
            ]
        }
        """

    Scenario: Keep it readonly for now
        When we post to "published"
        """
        [
            {"guid": "in_progress", "version": 1, "state": "in_progress"},
            {"guid": "published", "version": 1, "state": "published"}
        ]
        """
        Then we get error 401
