@wip
Feature: User Availability
    As an administrator
    I want to manage user availability records
    So that I can track when users are available or unavailable

    @auth
    Scenario: Create, Read, Update, Delete user availability
        # Create a new availability record
        When we post to "user_availability"
        """
        {
            "date": "2023-05-15",
            "status": "available",
            "language": ["en"],
            "working_hours": [
                {
                    "start_time": "09:00:00",
                    "end_time": "17:00:00",
                    "tags": [
                        {"code": "regular"}
                    ]
                }
            ]
        }
        """
        Then we get OK response
        And we get existing resource
        """
        {
            "user": "#CONTEXT_USER_ID#",
            "date": "2023-05-15",
            "status": "available",
            "language": ["en"],
            "working_hours": [
                {
                    "start_time": "09:00:00",
                    "end_time": "17:00:00"
                }
            ]
        }
        """
        
        # Read the created availability record
        When we get "/user_availability/#user_availability._id#"
        Then we get OK response
        And we get existing resource
        """
        {
            "user": "#CONTEXT_USER_ID#",
            "date": "2023-05-15",
            "status": "available",
            "language": ["en"],
            "working_hours": [
                {
                    "start_time": "09:00:00",
                    "end_time": "17:00:00"
                }
            ]
        }
        """
        
        # Update the availability record
        When we patch "/user_availability/#user_availability._id#"
        """
        {
            "status": "partial",
            "language": ["fr", "es"],
            "working_hours": [
                {
                    "start_time": "12:00:00",
                    "end_time": "16:00:00",
                    "tags": [
                        {"code": "half-day"}
                    ]
                }
            ]
        }
        """
        Then we get OK response
        And we get existing resource
        """
        {
            "user": "#CONTEXT_USER_ID#",
            "date": "2023-05-15", 
            "status": "partial",
            "language": ["fr", "es"],
            "working_hours": [
                {
                    "start_time": "12:00:00",
                    "end_time": "16:00:00"
                }
            ]
        }
        """
        
        # Search for availability by date
        When we get "/user_availability?where={"date":"2023-05-15"}"
        Then we get list with 1 items
        """
        {"_items": [{"date": "2023-05-15", "status": "partial", "language": ["fr", "es"]}]}
        """
        
        # Delete the availability record
        When we delete "/user_availability/#user_availability._id#"
        Then we get OK response
        
        # Verify deletion
        When we get "/user_availability/#user_availability._id#"
        Then we get error 404
