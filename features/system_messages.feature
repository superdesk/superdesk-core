Feature: System Messages

    @auth
    Scenario: List of empty system message
    Given empty "system_messages"
    When we get "/system_messages"
    Then we get list with 0 items

    @auth
    @notification
    Scenario: Create a new system message
        Given empty "system_messages"
        When we post to "system_messages"
	    """
        [{
            "is_active": true,
            "message_title": "This is message title",
            "message": "This is a message",
	        "type": "alert"
        }]
	    """
        Then we get new resource
        When we get "/system_messages"
        Then we get list with 1 items
	    """
        {"_items": [{
            "is_active": true,
            "message_title": "This is message title",
            "message": "This is a message",
	        "type": "alert",
	        "user_id": "#CONTEXT_USER_ID#"}]
        }
	    """

    @auth
    Scenario: Create a new system message with empty fields should give required error
        Given empty "system_messages"
        When we post to "system_messages"
	    """
        [{
            "is_active": true,
            "message_title": "This is message title",
	        "type": "alert",
	        "user_id": "#CONTEXT_USER_ID#"
        }]
	    """
        Then we get error 400
        """
        {
            "_error": {"code": 400, "message": "Insertion failure: 1 document(s) contain(s) error(s)"},
            "_issues": {"message": {"required": 1}},
            "_status": "ERR"
        }
        """

    @auth
    @notification
    Scenario: Update a system message
        Given empty "system_messages"
        When we post to "system_messages"
	    """
        [{
            "is_active": true,
            "message_title": "This is message title",
            "message": "This is a message",
	        "type": "alert",
	        "user_id": "#CONTEXT_USER_ID#"
        }]
	    """
        Then we get new resource
        When we get "/system_messages"
        Then we get list with 1 items
	    """
        {"_items": [{
            "is_active": true,
            "message_title": "This is message title",
            "message": "This is a message",
	        "type": "alert",
	        "user_id": "#CONTEXT_USER_ID#"}]
        }
	    """
        When we patch "/system_messages/#system_messages._id#"
        """
        {"message": "This is a updated message"}
        """
        Then we get updated response
	    """
        {
            "is_active": true,
            "message_title": "This is message title",
            "message": "This is a updated message",
	        "type": "alert",
	        "user_id": "#CONTEXT_USER_ID#"
        }
	    """

    @auth
    @notification
    Scenario: Delete a system message
        When we post to "system_messages"
	    """
        [{
            "is_active": true,
            "message_title": "This is message title",
            "message": "This is a message",
	        "type": "alert",
	        "user_id": "#CONTEXT_USER_ID#"
        }]
	    """
        Then we get OK response
        When we delete "/system_messages/#system_messages._id#"
        Then we get OK response