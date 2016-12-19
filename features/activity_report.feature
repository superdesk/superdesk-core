Feature: Activity report

    @auth
    Scenario: Activity report items
        Given "desks"
        """
        [{"name": "Sports Desk"}]
        """
        Given "archive"
        """
        [{"headline": "test_one", "task": {"desk": "#desks._id#"}, "keywords": ["testkey"], "subject":{"name": "education"}}]
        """
        When we post to "/activity_reports"
        """
        {"operation": "create", "desk": "#desks._id#", "keywords": ["testkey"], "subject": ["education"]}
        """
        Then we get new resource
        """
        {"operation": "create", "timestamp": "__any_value__", "report": 0}
        """
