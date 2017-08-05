Feature: Concept Items

    @auth
    Scenario: Create a new concept item and update it
        Given empty "concept_items"
        When we post to "concept_items"
        """
        {"first_name": "foo", "last_name": "bar", "email": "foo@bar.com", "by_line": "foo bar", "biography": "abc"}
        """
        Then we get existing resource
        """
        {
        	"_id": "#concept_items._id#",
        	"first_name": "foo",
        	"last_name": "bar",
        	"email": "foo@bar.com",
        	"by_line": "foo bar",
        	"biography": "abc"
        }
        """
		When we patch latest
			 """
            {"first_name": "new"}
             """
		Then we get updated response
            """
            {"first_name": "new"}
            """

    @auth
    Scenario: Delete a concept item
        Given empty "concept_items"
        When we post to "concept_items"
        """
        {"first_name": "foo", "last_name": "bar", "email": "foo@bar.com", "by_line": "foo bar", "biography": "abc"}
        """
        And we delete latest
        Then we get deleted response
