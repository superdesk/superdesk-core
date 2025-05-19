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
            ],
            "_generated": false
        }
        """
        
        # Search for availability by date
        When we get "/user_availability?where={"date":"2023-05-15"}"
        Then we get list with 1 items
        """
        {"_items": [{"date": "2023-05-15", "status": "partial", "language": ["fr", "es"]}]}
        """

        # Set the availability record empty
        When we patch "/user_availability/#user_availability._id#"
        """
        {
            "status": "not-set",
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
        

        
        # Delete the availability record
        When we delete "/user_availability/#user_availability._id#"
        Then we get OK response
        
        # Verify deletion
        When we get "/user_availability/#user_availability._id#"
        Then we get error 404

    @auth
    Scenario: Default user availability
        When we setup test user
        """
        {
            "username": "foo",
            "user_type": "user"
        }
        """
        # Create default availability settings using PUT
        When we put to "/default_user_availability/#CONTEXT_USER_ID#"
        """
        {
            "working_days": {
                "monday": {
                    "status": "available",
                    "working_hours": [
                        {
                            "start_time": "09:00:00",
                            "end_time": "17:00:00",
                            "tags": [
                                {"code": "regular"}
                            ]
                        }
                    ]
                },
                "tuesday": {
                    "status": "available",
                    "working_hours": [
                        {
                            "start_time": "09:00:00",
                            "end_time": "17:00:00",
                            "tags": [
                                {"code": "regular"}
                            ]
                        }
                    ]
                },
                "wednesday": {
                    "status": "partial",
                    "working_hours": [
                        {
                            "start_time": "09:00:00",
                            "end_time": "13:00:00",
                            "tags": [
                                {"code": "morning"}
                            ]
                        }
                    ]
                },
                "thursday": {
                    "status": "available",
                    "working_hours": [
                        {
                            "start_time": "09:00:00",
                            "end_time": "17:00:00",
                            "tags": [
                                {"code": "regular"}
                            ]
                        }
                    ]
                },
                "friday": {
                    "status": "available",
                    "working_hours": [
                        {
                            "start_time": "09:00:00",
                            "end_time": "16:00:00",
                            "tags": [
                                {"code": "regular"}
                            ]
                        }
                    ]
                },
                "saturday": {
                    "status": "unavailable"
                }
            },
            "language": ["en", "fr"],
            "tags": [
                {"code": "foo"},
                {"code": "bar"}
            ]
        }
        """
        Then we get OK response
        And we get existing resource
        """
        {
            "_id": "#CONTEXT_USER_ID#",
            "working_days": {
                "monday": {
                    "status": "available"
                },
                "tuesday": {
                    "status": "available"
                },
                "wednesday": {
                    "status": "partial"
                },
                "thursday": {
                    "status": "available"
                },
                "friday": {
                    "status": "available"
                },
                "saturday": {
                    "status": "unavailable"
                }
            },
            "language": ["en", "fr"]
        }
        """

        When we get "/user_availability"
        Then we get list with 30+ items
        """
        {"_items": [
            {"_generated": true, "status": "partial", "user": "#CONTEXT_USER_ID#", "language": ["en", "fr"]}
        ]}
        """
        
        # Get the default availability settings
        When we get "/default_user_availability/#CONTEXT_USER_ID#"
        Then we get OK response
        And we get existing resource
        """
        {
            "working_days": {
                "monday": {
                    "status": "available"
                },
                "wednesday": {
                    "status": "partial"
                },
                "saturday": {
                    "status": "unavailable"
                }
            },
            "language": ["en", "fr"]
        }
        """
        
        # Update the default availability settings
        When we put to "/default_user_availability/#CONTEXT_USER_ID#"
        """
        {
            "working_days": {
                "monday": {
                    "status": "partial",
                    "working_hours": [
                        {
                            "start_time": "09:00:00",
                            "end_time": "13:00:00",
                            "tags": [
                                {"code": "morning"}
                            ]
                        }
                    ]
                },
                "tuesday": {
                    "status": "partial",
                    "working_hours": [
                        {
                            "start_time": "13:00:00",
                            "end_time": "17:00:00",
                            "tags": [
                                {"code": "afternoon"}
                            ]
                        }
                    ]
                },
                "wednesday": {
                    "status": "unavailable"
                },
                "thursday": {
                    "status": "available",
                    "working_hours": [
                        {
                            "start_time": "09:00:00",
                            "end_time": "17:00:00",
                            "tags": [
                                {"code": "regular"}
                            ]
                        }
                    ]
                },
                "friday": {
                    "status": "available",
                    "working_hours": [
                        {
                            "start_time": "09:00:00",
                            "end_time": "16:00:00",
                            "tags": [
                                {"code": "regular"}
                            ]
                        }
                    ]
                },
                "saturday": {
                    "status": "unavailable"
                },
                "sunday": {
                    "status": "unavailable"
                }
            },
            "language": ["en"]
        }
        """
        Then we get OK response
        And we get existing resource
        """
        {
            "working_days": {
                "monday": {
                    "status": "partial"
                },
                "tuesday": {
                    "status": "partial"
                },
                "wednesday": {
                    "status": "unavailable"
                },
                "thursday": {
                    "status": "available"
                }
            },
            "language": ["en"]
        }
        """
        
        # Verify that PATCH is not allowed
        When we patch "/default_user_availability/#CONTEXT_USER_ID#"
        """
        {
            "language": ["en", "es"]
        }
        """
        Then we get error 405
        
        # Verify that DELETE is not allowed
        When we delete "/default_user_availability/#CONTEXT_USER_ID#"
        Then we get error 405
        
        # Try to update someone else's default availability
        Given "users"
        """
        [
            {"username": "user2", "password": "test_password", "email": "test@example.com"}
        ]
        """
        When we put to "/default_user_availability/#users._id#"
        """
        {
            "working_days": {
                "monday": {"status": "unavailable"}
            }
        }
        """
        Then we get error 403

        # Verify that POST is not allowed
        When we post to "default_user_availability"
        """
        {
            "working_days": {
                "monday": {"status": "available"}
            }
        }
        """
        Then we get error 405

        When we put to "/default_user_availability/#CONTEXT_USER_ID#"
        """
        {"working_days": {}}
        """
        And we get "user_availability"
        Then we get list with 0 items

        When we put to "/default_user_availability/#CONTEXT_USER_ID#"
        """
        {"working_days": {"monday": {"status": "available"}}}
        """

        And we get "user_availability"
        Then we get list with 10+ items

        When we put to "/default_user_availability/#CONTEXT_USER_ID#"
        """
        {"language": ["de"]}
        """
        And we post to "/user_availability"
        """
        {
            "date": "2023-05-15",
            "status": "available"
        }
        """
        Then we get OK response
        And we get existing resource
        """
        {
            "date": "2023-05-15",
            "language": ["de"]
        }
        """

        When we setup test user
        """
        {
            "username": "bar",
            "user_type": "user"
        }
        """
        When we put to "/default_user_availability/#FOO_USER_ID#"
        """
        {"enabled": false}
        """
        Then we get error 403
