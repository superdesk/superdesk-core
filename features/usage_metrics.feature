Feature: Usage Metrics

    @auth
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
        When we post to "/usage-metrics"
        """
        {
            "action": "preview",
            "user": "#users._id#",
            "item": "#archive._id#",
            "date": "2021-03-01T12:56:00+0000"
        }
        """
        Then we get new resource
