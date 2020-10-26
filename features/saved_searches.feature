Feature: Saved Searches

    @auth
    Scenario: Create a Saved Search
        Given empty "saved_searches"
        When we post to "/saved_searches"
        """
        {
        "name": "cricket",
        "filter": {"query": {"q": "cricket", "repo": "archive"}}
        }
        """
        Then we get new resource
        """
        {"filter": {"query": {"q": "cricket", "repo": "archive"}}}
        """
        When we get "/saved_searches"
        Then we get list with 1 items
        """
        {"_items": [
            {"filter": {"query": {"q": "cricket", "repo": "archive"}}}
        ]}
        """
        When we get "/saved_searches/#saved_searches._id#"
        Then we get existing resource
        """
        {"filter": {"query": {"q": "cricket", "repo": "archive"}}}
        """

    @auth
    Scenario: Create a Global Saved Search
        Given empty "saved_searches"
        When we post to "/saved_searches"
        """
        {
        "name": "cricket",
        "filter": {"query": {"q": "cricket", "repo": "archive"}},
        "is_global": true
        }
        """
        Then we get response code 201
        When we get "/saved_searches"
        Then we get list with 1 items

    @auth
    Scenario: Create a Saved Search with facets
        Given empty "saved_searches"
        When we post to "/saved_searches"
        """
        {
        "name": "cricket and text and from AAP",
        "filter":{"query":{"q":"cricket","repo":"ingest","type": ["text"], "source": ["AAP"]}}
        }
        """
        Then we get response code 201

    @auth
    Scenario: A user shouldn't see another user's searches but all saved searches will show them
        Given empty "saved_searches"
        When we post to "/users"
        """
        {"username": "save_search", "password": "bar", "display_name": "Joe Black", "email": "joe@black.com", "is_active": true, "sign_off": "abc"}
        """
        When we login as user "save_search" with password "bar" and user type "admin"
        When we post to "/saved_searches"
        """
        {
        "name": "basket ball",
        "filter": {"query": {"q": "basket ball", "repo": "ingest"}}
        }
        """
        When we switch user
        When we post to "/saved_searches"
        """
        {
        "name": "cricket",
        "filter": {"query": {"q": "cricket", "repo": "archive"}}
        }
        """
        When we get "/saved_searches"
        Then we get list with 1 items
        When we login as user "save_search" with password "bar" and user type "admin"
        When we get "/saved_searches"
        Then we get list with 1 items

        When we get "/all_saved_searches"
        Then we get list with 2 items

    @auth
    Scenario: A user should see another user's global searches
        Given empty "saved_searches"
        When we post to "/users"
        """
        {"username": "save_search", "password": "bar", "display_name": "Joe Black", "email": "joe@black.com", "is_active": true, "sign_off": "abc"}
        """
        When we login as user "save_search" with password "bar" and user type "admin"
        And we post to "/saved_searches"
        """
        {
        "name": "basket ball",
        "filter": {"query": {"q": "basket ball", "repo": "ingest"}},
        "description": "abc",
        "is_global": true
        }
        """
        When we switch user
        When we post to "/saved_searches"
        """
        {
        "name": "cricket",
        "filter": {"query": {"q": "cricket", "repo": "archive"}}
        }
        """
        When we get "/saved_searches"
        Then we get list with 2 items
        When we login as user "save_search" with password "bar" and user type "admin"
        When we get "/saved_searches"
        Then we get list with 1 items
        When we get "/all_saved_searches"
        Then we get list with 2 items

    @auth
    Scenario: Create a Saved Search without a name
        Given empty "saved_searches"
        When we post to "/saved_searches"
        """
        {
        "filter": {"query": {"q": "cricket", "repo": "archive"}}
        }
        """
        Then we get error 400
		"""
      	{"_error": {"code": 400, "message": "Insertion failure: 1 document(s) contain(s) error(s)"}, "_issues": {"name": {"required": 1}}, "_status": "ERR"}
      	"""

    @auth
    Scenario: Create a Saved Search without a filter
        Given empty "saved_searches"
        When we post to "/saved_searches"
        """
        {
        "name": "cricket"
        }
        """
        Then we get error 400
		"""
      	{"_error": {"code": 400, "message": "Insertion failure: 1 document(s) contain(s) error(s)"}, "_issues": {"filter": {"required": 1}}, "_status": "ERR"}
      	"""

    @auth
    Scenario: Create a Saved Search with invalid filter
        Given empty "saved_searches"
        When we post to "/saved_searches"
        """
        {
        "name": "cricket",
        "filter": {"abc": "abc"}
        }
        """
        Then we get error 400
	    """
	    {"_message": "Search cannot be saved without a filter!", "_status": "ERR"}
	    """

	@auth
    Scenario: Update a Saved Search
        Given empty "saved_searches"
        When we post to "/saved_searches"
        """
        {
        "name": "cricket",
        "filter": {"query": {"q": "cricket"}}
        }
        """
        Then we get response code 201
        When we patch "/saved_searches"
        """
        {
        "name": "Cricket"
        }
        """
        Then we get response code 405

	@auth
    Scenario: Update a global Saved Search with success
        Given empty "saved_searches"
        When we post to "/saved_searches"
        """
        {
        "name": "cricket",
        "filter": {"query": {"q": "cricket"}},
        "is_global": true
        }
        """
        Then we get response code 201
        When we patch "/saved_searches/#saved_searches._id#"
        """
        {
        "filter": {"query": {"q": "baseball"}}
        }
        """
        Then we get response code 200

    @auth
    @provider
    Scenario: Create a Saved Search and retrieve content
    	Given empty "ingest"
        When we fetch from "reuters" ingest "tag_reuters.com_2014_newsml_KBN0FL0NM:10"
        Given empty "saved_searches"
        When we post to "/saved_searches"
        """
        {
        "name": "US Pictures",
        "filter": {"query": {"q": "term", "repo": "ingest", "type": ["picture"]}}
        }
        """
        Then we get response code 201
        When we get "/saved_searches/#saved_searches._id#"
        Then we get existing saved search
        """
        {
        "name": "US Pictures",
        "filter": {"query": {"repo": "ingest", "q": "term", "type": ["picture"]}}
        }
        """
        When we get "/saved_searches/#saved_searches._id#/items"
        Then we get list with 3 items
		"""
		{
		    "_items": [{
		        "type": "picture",
		        "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F0MS:2",
		        "state": "ingested"
		    }, {
		        "type": "picture",
		        "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F0MT:2",
		        "state": "ingested"
		    }, {
		        "type": "picture",
		        "guid": "tag_reuters.com_2014_newsml_LYNXMPEA6F13M:1",
		        "state": "ingested"
		    }]
		}
		"""

    @auth
    Scenario: A user cannot update another user's search
        Given empty "saved_searches"
        When we post to "/users"
        """
        {"username": "save_search", "password": "bar", "display_name": "Joe Black", "email": "joe@black.com", "is_active": true, "sign_off": "abc"}
        """
        When we login as user "save_search" with password "bar" and user type "admin"
        And we post to "/saved_searches"
        """
        {
        "name": "basket ball",
        "filter": {"query": {"q": "basket ball", "repo": "ingest"}},
        "description": "abc"
        }
        """
        When we switch user
        When we patch "/users/#USERS_ID#"
        """
        {"user_type": "user", "privileges": {"global_saved_searches" : 0}}
        """
        When we patch "/saved_searches/#saved_searches._id#"
        """
        {"description": "abc123"}
        """
        Then we get response code 403

    @auth
    Scenario: A user with global search/admin privilege can update another user's global search
        Given empty "saved_searches"
        When we post to "/users"
        """
        {"username": "save_search", "password": "bar", "display_name": "Joe Black", "email": "joe@black.com", "is_active": true, "sign_off": "abc"}
        """
        When we login as user "save_search" with password "bar" and user type "admin"
        And we post to "/saved_searches"
        """
        {
        "name": "basket ball",
        "filter": {"query": {"q": "basket ball", "repo": "ingest"}},
        "description": "abc",
        "is_global": true
        }
        """
        When we switch user
        When we patch "/saved_searches/#saved_searches._id#"
        """
        {"description": "abc123"}
        """
        Then we get response code 200
        When we patch "/saved_searches/#saved_searches._id#"
        """
        {
        "name": "volleyball",
        "filter": {"query": {"q": "volley ball", "repo": "ingest"}}
        }
        """
        When we get "/saved_searches/#saved_searches._id#"
        Then we get existing saved search
        """
        {
            "name": "volleyball",
            "filter": {"query": {"q": "volley ball", "repo": "ingest"}}
        }
        """

    @auth
    Scenario: A user with global search/admin privilege cannot update another user's local search
        Given empty "saved_searches"
        When we post to "/users"
        """
        {"username": "save_search", "password": "bar", "display_name": "Joe Black", "email": "joe@black.com", "is_active": true, "sign_off": "abc"}
        """
        When we login as user "save_search" with password "bar" and user type "admin"
        And we post to "/saved_searches"
        """
        {
        "name": "basket ball",
        "filter": {"query": {"q": "basket ball", "repo": "ingest"}},
        "description": "abc"
        }
        """
        When we switch user
        When we patch "/saved_searches/#saved_searches._id#"
        """
        {"description": "abc123"}
        """
        Then we get response code 400

    @auth
    @notification
    Scenario: Push notification on delete
        When we post to "/saved_searches"
        """
        {"name": "test", "filter": {"query": {"q": "test"}}}
        """
        When we reset notifications
        And we delete "/saved_searches/#saved_searches._id#"
        Then we get OK response
        And we get notifications
        """
        [{"event": "savedsearch:update"}]
        """

    @auth
    Scenario: A user cannot delete another user's search
        Given empty "saved_searches"
        When we post to "/users"
        """
        {"username": "save_search", "password": "bar", "display_name": "Joe Black", "email": "joe@black.com", "is_active": true, "sign_off": "abc"}
        """
        When we login as user "save_search" with password "bar" and user type "admin"
        And we post to "/saved_searches"
        """
        {
        "name": "basket ball",
        "filter": {"query": {"q": "basket ball", "repo": "ingest"}},
        "description": "abc"
        }
        """
        When we switch user
        When we patch "/users/#USERS_ID#"
        """
        {"user_type": "user", "privileges": {"global_saved_searches" : 0}}
        """
        When we delete "/saved_searches/#saved_searches._id#"
        Then we get response code 403

    @auth
    Scenario: A user with global search privilege can delete another user's search
        Given empty "saved_searches"
        When we post to "/users"
        """
        {"username": "save_search", "password": "bar", "display_name": "Joe Black", "email": "joe@black.com", "is_active": true, "sign_off": "abc"}
        """
        When we login as user "save_search" with password "bar" and user type "admin"
        And we post to "/saved_searches"
        """
        {
        "name": "basket ball",
        "filter": {"query": {"q": "basket ball", "repo": "ingest"}},
        "description": "abc",
        "is_global": true
        }
        """
        When we switch user
        When we delete "/saved_searches/#saved_searches._id#"
        Then we get response code 204

    @auth
    Scenario: Add saved search with empty repo
        When we post to "/saved_searches"
        """
        {
            "name": "foo",
            "filter": {
                "query": {
                    "repo": "",
                    "q": "headline:test",
                    "spike": "exclude"
                }
            }
        }
        """
        Then we get new resource