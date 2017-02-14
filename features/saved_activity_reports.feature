Feature: Saved Activity Reports

    @auth
    Scenario: Create activity report
        Given empty "desks"
        Given empty "saved_activity_reports"
        When we post to "/desks"
        """
        {"name": "Breaking News"}
        """
        And we post to "/saved_activity_reports" with success
        """
        {
        	"operation": "publish",
        	"desk": "#desks._id#",
        	"operation_date_start": "2016-02-13",
        	"operation_date_end": "2016-02-14",
        	"name": "report1",
        	"description": "activity report",
        	"is_global": true
        }
        """
        Then we get new resource
        """
        {
        	"operation": "publish",
        	"desk": "#desks._id#",
        	"operation_date_start": "2016-02-13T00:00:00+0000",
        	"operation_date_end": "2016-02-14T00:00:00+0000",
        	"name": "report1",
        	"description": "activity report",
        	"is_global": true
        }
        """
