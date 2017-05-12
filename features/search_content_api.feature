Feature: Content API Search features
    Background:
        Given "items"
        """
        [
            {
                "_id" : "1",
                "service" : [{"name" : "Finance", "code" : "f"}],
                "subject" : [{"name" : "economy, business and finance", "code" : "04000000"}],
                "_current_version" : 2,
                "type" : "text",
                "versioncreated" : "2017-05-09T02:55:53.000+0000",
                "firstcreated" : "2017-05-09T02:55:09.000+0000",
                "headline" : "This is article has no media",
                "subscribers" : ["sub1", "sub2"],
                "priority" : 6,
                "version" : 2,
                "located" : "Melbourne",
                "urgency" : 3,
                "language" : "en",
                "source": "XYZ",
                "body_html" : "<p>This is article has featuremedia</p>",
                "pubstatus" : "usable",
                "genre" : [{"name" : "Article (news)", "code" : "Article"}],
                "profile" : "TextwithMedia",
                "slugline" : "Slugline here",
                "associations": {
                    "featuremedia": {
                        "guid": "featuremedia",
                        "subscribers" : ["sub1"]
                    }
                }
            },
            {
                "_id" : "2",
                "service" : [{"name" : "National", "code" : "a"}],
                "subject" : [{"name" : "Sports", "code" : "15000000"}],
                "_current_version" : 2,
                "type" : "text",
                "versioncreated" : "2017-05-09T02:55:53.000+0000",
                "firstcreated" : "2017-05-09T02:55:09.000+0000",
                "headline" : "foo bar",
                "subscribers" : ["sub2"],
                "priority" : 1,
                "version" : 2,
                "source": "ABC",
                "located" : "Melbourne",
                "urgency" : 1,
                "language" : "en",
                "body_html" : "<p>This is article has featuremedia</p>",
                "pubstatus" : "usable",
                "genre" : [{"name" : "Article (news)", "code" : "Article"}],
                "profile" : "TextwithMedia",
                "slugline" : "Slugline here"
            }
        ]
        """

    @auth
    Scenario: Control access to Content API via privilege
        When we get "/search_capi"
        Then we get list with 2 items
        When we get "/search_capi/1"
        Then we get OK response
        When we login as user "foo" with password "bar" and user type "user"
        """
        {"user_type": "user", "email": "foo.bar@foobar.org"}
        """
        And we get "/search_capi"
        Then we get error 403
        When we get "/search_capi/1"
        Then we get error 403

    @auth
    Scenario: Search content api using parameters
        When we get "/search_capi"
        Then we get list with 2 items
        When we get "/search_capi?q=foo"
        Then we get list with 1 items
        """
        {
            "_items": [{"_id": "2", "headline" : "foo bar"}]
        }
        """
        When we get "/search_capi?q=article"
        Then we get list with 2 items
        """
        {
            "_items": [
                {"_id": "2", "headline" : "foo bar"},
                {"_id": "1", "headline" : "This is article has no media"}
            ]
        }
        """
        When we get "/search_capi?priority=1"
        Then we get list with 1 items
        """
        {
            "_items": [
                {"_id": "2", "headline" : "foo bar", "priority": 1}
            ]
        }
        """
        When we get "/search_capi?priority=[1,6]"
        Then we get list with 2 items
        """
        {
            "_items": [
                {"_id": "2", "headline" : "foo bar"},
                {"_id": "1", "headline" : "This is article has no media"}
            ]
        }
        """
        When we get "/search_capi?urgency=1"
        Then we get list with 1 items
        """
        {
            "_items": [
                {"_id": "2", "headline" : "foo bar", "priority": 1}
            ]
        }
        """
        When we get "/search_capi?urgency=[1,3]"
        Then we get list with 2 items
        """
        {
            "_items": [
                {"_id": "2", "headline" : "foo bar"},
                {"_id": "1", "headline" : "This is article has no media"}
            ]
        }
        """
        When we get "/search_capi?service=a"
        Then we get list with 1 items
        """
        {
            "_items": [
                {"_id": "2", "anpa_category" : [{"name" : "National", "qcode" : "a"}]}
            ]
        }
        """
        When we get "/search_capi?service=["a","f"]"
        Then we get list with 2 items
        """
        {
            "_items": [
                {"_id": "1", "anpa_category" : [{"name" : "Finance", "qcode" : "f"}]},
                {"_id": "2", "anpa_category" : [{"name" : "National", "qcode" : "a"}]}
            ]
        }
        """
        When we get "/search_capi?item_source=XYZ"
        Then we get list with 1 items
        """
        {
            "_items": [
                {"_id": "1", "source": "XYZ"}
            ]
        }
        """
        When we get "/search_capi?item_source=["XYZ","ABC"]"
        Then we get list with 2 items
        """
        {
            "_items": [
                {"_id": "1", "source": "XYZ"},
                {"_id": "2", "source": "ABC"}
            ]
        }
        """
        When we get "/search_capi?subject=04000000"
        Then we get list with 1 items
        """
        {
            "_items": [
                {"_id": "1", "subject": [{"qcode": "04000000"}]}
            ]
        }
        """
        When we get "/search_capi?subject=["04000000","15000000"]"
        Then we get list with 2 items
        """
        {
            "_items": [
                {"_id": "1", "subject": [{"qcode": "04000000"}]},
                {"_id": "2", "subject": [{"qcode": "15000000"}]}
            ]
        }
        """
        When we get "/search_capi?subject=04000000&item_source=XYZ"
        Then we get list with 1 items
        """
        {
            "_items": [
                {"_id": "1", "subject": [{"qcode": "04000000"}], "source": "XYZ"}
            ]
        }
        """
        When we get "/search_capi?filter=[{"terms":{"service.code": ["f"]}}, {"term": {"urgency": 3}}]"
        Then we get list with 1 items
        """
        {
            "_items": [
                {"_id": "1", "anpa_category" : [{"name" : "Finance", "qcode" : "f"}], "urgency": 3}
            ]
        }
        """

    @auth
    Scenario: Search content api by subscribers
        When we get "/search_capi"
        Then we get list with 2 items
        When we get "/search_capi?subscribers=sub1"
        Then we get list with 1 items
        """
        {
            "_items": [
                {
                    "_id": "1", "headline" : "This is article has no media",
                    "subscribers": ["sub1", "sub2"],
                    "associations": {
                        "featuremedia": {
                            "_id": "featuremedia"
                        }
                    }
                }
            ]
        }
        """
        When we get "/search_capi?subscribers=sub2"
        Then we get list with 2 items
        """
        {
            "_items": [
                {
                    "_id": "1", "headline" : "This is article has no media",
                    "subscribers": ["sub1", "sub2"],
                    "associations": {}
                },
                {
                    "_id": "2", "headline" : "foo bar",
                    "subscribers": ["sub2"],
                    "associations": {}
                }
            ]
        }
        """
        When we get "/search_capi?subscribers=xxx"
        Then we get list with 0 items
