Feature: ActivityReports

    @auth
    Scenario: Create activity report
        Given empty "desks"
        Given empty "activityreports"
        When we post to "/desks"
            """
            {"name": "Breaking News"}
            """
        And we post to "/activityreports"
            """
            {"operation": "publish", "desk": "#desks._id#", "date": "2016-02-13T00:00:00.000Z"}
            """
        Then we get new resource
        """
        {"operation": "publish", "desk": "#desks._id#", "date": "2016-02-13T00:00:00+0000"}
        """
