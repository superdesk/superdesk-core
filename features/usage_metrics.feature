Feature: Usage Metrics

    @auth
    @notification
    Scenario: Track item activity
        Given "users"
        """
        [
            {"username": "foo"}
        ]
        """
        And "archive"
        """
        [
            {"_id": "abcd"}
        ]
        """
        When we patch "archive/abcd"
        """
        {"headline": "do some action to avoid user last activity notification later"}
        """
        Then we get OK response

        When we reset notifications
        And we post to "/usage-metrics"
        """
        {
            "action": "preview",
            "user": "#users._id#",
            "item": "#archive._id#",
            "date": "2021-03-01T12:56:00+0000"
        }
        """
        Then we get new resource

        When we get "archive/abcd"
        Then we get existing resource
        """
        {
            "metrics": {
                "preview": 1
            }
        }
        """
        And we get 0 notifications