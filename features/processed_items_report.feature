Feature: Processed Items Report
     
     @auth
     Scenario: Processed published report
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
		    "subject":[{"qcode": "05007000", "name": "sub"}],
			"firstcreated": "2017-01-02T09:03:26+0000",
		    "body_html": "Test Document body"
		}]
		"""
		When we publish "#archive._id#" with "publish" type and "published" state
		Then we get OK response
		When we post to "/processed_items_report" with success
        """
        {
        	"user": "#CONTEXT_USER_ID#",
        	"starting_time": "2017-01-02T09:03:26+0000",
        	"ending_time": "2017-02-06T09:03:26+0000"
        }
        """
        Then we get existing resource
        """
        {
        "user": "#CONTEXT_USER_ID#",
        "starting_time": "2017-01-02T09:03:26+0000",
        "ending_time": "2017-02-06T09:03:26+0000",
        "report": {"corrected_items": 0,"killed_items": 0,"total_items": 2,"published_items": 2, "spiked_items": 0}
        }
        """
    @auth
    Scenario: Processed spiked items
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
		    "subject":[{"qcode": "05007000", "name": "sub"}],
			"firstcreated": "2017-01-02T09:03:26+0000",
		    "body_html": "Test Document body"
		}]
		"""
        When we spike "item1"
		Then we get OK response
		When we post to "/processed_items_report" with success
        """
        {
        	"user": "#CONTEXT_USER_ID#",
        	"starting_time": "2017-01-02T09:03:26+0000",
        	"ending_time": "2017-02-06T09:03:26+0000"
        }
        """
        Then we get existing resource
        """
        {
        "user": "#CONTEXT_USER_ID#",
        "starting_time": "2017-01-02T09:03:26+0000",
        "ending_time": "2017-02-06T09:03:26+0000",
        "report": {"corrected_items": 0,"killed_items": 0,"total_items": 1,"published_items": 0, "spiked_items": 1}
        }
        """
   	@auth
   	Scenario: Processed corrected items
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
			"state": "published",
		    "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
		    "subject":[{"qcode": "05007000", "name": "sub"}],
			"firstcreated": "2017-01-02T09:03:26+0000",
		    "body_html": "Test Document body"
		}]
		"""
		When we publish "#archive._id#" with "correct" type and "corrected" state
    	Then we get OK response
    	When we post to "/processed_items_report" with success
        """
        {
        	"user": "#CONTEXT_USER_ID#",
        	"starting_time": "2017-01-02T09:03:26+0000",
        	"ending_time": "2017-02-06T09:03:26+0000"
        }
        """
        Then we get existing resource
        """
        {
        "user": "#CONTEXT_USER_ID#",
        "starting_time": "2017-01-02T09:03:26+0000",
        "ending_time": "2017-02-06T09:03:26+0000",
        "report": {"corrected_items": 2,"killed_items": 0,"total_items": 2,"published_items": 0, "spiked_items": 0}
        }
        """
  	@auth
  	Scenario: Processed killed items
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
			"state": "published",
		    "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
		    "subject":[{"qcode": "05007000", "name": "sub"}],
			"firstcreated": "2017-01-02T09:03:26+0000",
		    "body_html": "Test Document body"
		}]
		"""
		When we publish "#archive._id#" with "kill" type and "killed" state
    	Then we get OK response
		When we post to "/processed_items_report" with success
        """
        {
        	"user": "#CONTEXT_USER_ID#",
        	"starting_time": "2017-01-02T09:03:26+0000",
        	"ending_time": "2017-02-06T09:03:26+0000"
        }
        """
        Then we get existing resource
        """
        {
        "user": "#CONTEXT_USER_ID#",
        "starting_time": "2017-01-02T09:03:26+0000",
        "ending_time": "2017-02-06T09:03:26+0000",
        "report": {"corrected_items": 0,"killed_items": 2,"total_items": 2, "published_items": 0, "spiked_items": 0}
        }
        """