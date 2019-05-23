Feature: Search Provider Feature

    @auth
    Scenario: List empty providers
        Given empty "search_providers"
        When we get "/search_providers"
        Then we get list with 0 items

    @auth
    Scenario: Create a new Search Provider
        Given empty "search_providers"
        When we post to "search_providers"
	    """
        [{"search_provider": "testsearch", "source": "testsearch", "config": {"password":"", "username":""}, "name": "test"}]
	    """
        Then we get new resource
        When we get "/search_providers"
        Then we get list with 1 items
	    """
        {"_items": [{"search_provider": "testsearch", "source": "testsearch", "is_closed": false, "config": {"password":"", "username":""}, "name": "test"}]}
	    """

    @auth
    Scenario: Creating a Search Provider fails if the search provider type hasn't been registered with the application
        Given empty "search_providers"
        When we post to "search_providers"
	    """
        [{"search_provider": "Multimedia", "source": "aapmm", "config": {"password":"", "username":""}}]
	    """
        Then we get error 400
        """
        {"_status": "ERR", "_issues": {"search_provider": "unallowed value Multimedia"}}
        """

    @auth
    Scenario: Updating an existing search provider fails if the search provider type hasn't been registered with the application
        Given empty "search_providers"
        When we post to "search_providers"
	    """
        [{"search_provider": "testsearch", "source": "testsearch", "config": {"password":"", "username":""}}]
	    """
        When we patch "search_providers/#search_providers._id#"
        """
        {"search_provider": "Multimedia", "source": "AAP Multimedia"}
        """
        Then we get error 400
        """
        {"_status": "ERR",  "_issues": {"search_provider": "unallowed value Multimedia"}}
        """

    @auth
    Scenario: Deleting a Search Provider is allowed if no articles have been fetched from this search provider
        Given empty "search_providers"
        When we post to "search_providers"
	    """
        [{"search_provider": "testsearch", "source": "testsearch", "config": {"password":"", "username":""}}]
	    """
        When we delete "search_providers/#search_providers._id#"
        Then we get response code 204

    @auth
    Scenario: Get list of registered search providers
        When we get "allowed_values"
        Then we get existing resource
        """
        {"_items": [{"_id": "search_providers.search_provider", "items": ["testsearch"]}]}
        """

    @auth
    Scenario: Search using custom search provider
        Given "search_providers"
        """
        [{"search_provider": "testsearch", "source": "testsearch", "config": {"password":"", "username":""}}]
        """
        Given "desks"
        """
        [{"name": "sports"}]
        """
        When we get "search_providers_proxy?repo=#search_providers._id#"
        Then we get list with 1 items
        """
        {"_items": [{
            "_id": "foo",
            "guid": "foo",
            "_type": "externalsource",
            "pubstatus": "usable",
            "fetch_endpoint": "search_providers_proxy"
        }]}
        """

        When we post to "search_providers_proxy?repo=#search_providers._id#"
        """
        {"guid": "foo", "desk": "#desks._id#"}
        """
        Then we get OK response
        When we get "/archive/#search_providers_proxy._id#"
        Then we get existing resource
        """
        {
            "ingest_id": "foo",
            "_id": "#search_providers_proxy._id#",
            "source": "bar",
            "ingest_provider": "#search_providers._id#",
            "type": "picture",
            "headline": "foo"
        }
        """


    @auth
    Scenario: Get available search providers
        When we get "search_providers_allowed"
        Then we get list with 1+ items
        """
        {"_items": [{"search_provider": "testsearch", "label": "Foo"}]}
        """

    @auth
    Scenario: Let search proxy work for ingest/archive/etc
        When we post to "archive"
        """
        {"guid": "foo", "version": 1, "type": "text"}
        """

        When we get "search_providers_proxy?repo=archive"
        Then we get list with 1 items
        """
        {"_items": [{
            "_type": "archive",
            "guid": "foo",
            "pubstatus": "usable"
        }]}
        """

        When we get "search_providers_proxy?repo=published,ingest"
        Then we get list with 0 items