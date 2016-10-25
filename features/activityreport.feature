Feature: Activity report

    @auth
    Scenario: Activity report items
        Given "desks"
        """
        [{"name": "Sports Desk"}]
        """
        Given "archive"
            """
            [{"headline": "test_one", "task": {"desk": "#desks._id#"}}]
            """
        When we get "/archive"
        Then we get list with 1 items
        When we post to "/activityreports"
        """
        {"operation": "create", "desk": "#desks._id#"}
        """
        When we get "/activityreports/#activityreports._id#"
        Then we get existing resource
        """
        {"report": 0}
        """
