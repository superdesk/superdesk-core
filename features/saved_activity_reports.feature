Feature: SavedActivityReports

    @auth
    Scenario: Create activity report
        Given empty "desks"
        Given empty "saved_activity_reports"
        When we post to "/desks"
            """
            {"name": "Breaking News"}
            """
        And we post to "/saved_activity_reports"
            """
            {"operation": "publish", "desk": "#desks._id#", "operation_date": "2016-02-13T00:00:00.000Z"}
            """
        Then we get new resource
        """
        {"operation": "publish", "desk": "#desks._id#", "operation_date": "2016-02-13T00:00:00+0000"}
        """
