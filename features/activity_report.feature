Feature: Activity report

    @auth
    Scenario: Activity report items
        Given "desks"
        """
        [{"name": "Sports Desk"}]
        """
        Given "archive"
		"""
		[{
			"guid": "item1",
			"type": "text",
			"headline": "item1",
			"_current_version": 1,
			"state": "fetched",
		    "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
		    "subject":[{"qcode": "05007000", "name": "university"}],
		    "keywords": ["UNIVERSITY"],
		    "slugline": "test",
		    "priority": 6,
		    "urgency": 3,
		    "target_subscribers": [{"name":"test"}],
		    "anpa_category": [{"name": "arts, culture and entertainment" , "qcode": "01000000"}],
		    "body_html": "Test Document body"
		}]
        """
	    When we publish "#archive._id#" with "publish" type and "published" state
	    Then we get OK response
        When we post to "/activity_reports" with success
        """
        {
        	"operation": "publish",
        	"desk": "#desks._id#",
        	"operation_date": "#DATE#",
        	"subject":[{"qcode": "05007000", "name": "university"}],
        	"keywords": ["UNIVERSITY"],
        	"priority": 6,
        	"urgency": 3,
        	"category": [{"name": "arts, culture and entertainment" , "qcode": "01000000"}],
        	"subscriber": "test"
        }
        """
        Then we get existing resource
        """
        {
        	"subject":[{"qcode": "05007000", "name": "university"}],
        	"keywords": ["UNIVERSITY"],
        	"priority": 6,
        	"urgency":3,
        	"subscriber": "test",
        	"category": [{"name": "arts, culture and entertainment" , "qcode": "01000000"}],
        	"report": {"items": 2}
        }
        """
        When we post to "/activity_reports" with success
        """
        {
        	"operation": "publish",
        	"desk": "#desks._id#",
        	"operation_date": "#DATE#",
        	"group_by": ["desk"],
        	"subject":[{"qcode": "05007000", "name": "university"}],
        	"keywords": ["UNIVERSITY"],
        	"priority": 6,
        	"urgency":3,
        	"category": [{"name": "arts, culture and entertainment" , "qcode": "01000000"}],
        	"subscriber": "test"
        }
        """
        Then we get existing resource
        """
        {
        	"operation": "publish",
        	"desk": "#desks._id#",
        	"group_by": ["desk"],
        	"subject":[{"qcode": "05007000", "name": "university"}],
        	"keywords": ["UNIVERSITY"],
        	"priority": 6,
        	"urgency":3,
        	"category": [{"name": "arts, culture and entertainment" , "qcode": "01000000"}],
        	"subscriber": "test",
        	"report": [{"desk": "Sports Desk", "items": 2}]
        }
        """
	