Feature: Track usage of an item

    @auth
    Scenario: We can get links to an item
        Given "archive"
        """
        [
            {"_id": "one", "guid": "one", "type": "text", "version": 1},
            {"_id": "two", "guid": "two", "type": "picture", "version": 1},
            {"_id": "three", "guid": "guid3", "type": "video", "version": 1}
        ]
        """
        And "vocabularies"
        """
        [
            {"_id": "related", "field_type": "related_content"}
        ]
        """

        When we get "links?where={"guid":"one"}"
        Then we get list with 0 items

        When we patch "/archive/one"
        """
        {"associations": {"pic": {"_id": "two", "type": "picture", "renditions": {}}}}
        """
        Then we get OK response

        When we get "links?where={"guid": "two"}"
        Then we get list with 1 items
        """
        {"_items": [
            {"_id": "one", "type": "text", "versioncreated": "__now__"}
        ]}
        """

        When we get "archive/two"
        Then we get existing resource
        """
        {"_id": "two", "used": true, "used_count": 1, "used_updated": "__now__"}
        """

        When we patch "/archive/one"
        """
        {"associations": {"related--1": {"_id": "three", "type": "video"}}}
        """
        Then we get OK response

        When we get "links?where={"guid": "guid3"}"
        Then we get list with 1 items
        """
        {"_items": [
            {"_id": "one", "type": "text", "versioncreated": "__now__"}
        ]}
        """

        When we get "/archive/three"
        Then we get existing resource
        """
        {"used": true, "used_updated": "__now__"}
        """

        When we patch "/archive/one"
        """
        {"associations": {"external--1": {"_id": "externalid", "uri": "externaluri", "type": "video"}}}
        """
        Then we get OK response

        When we get "links?where={"uri":"externaluri", "guid": "fetchedid"}"
        Then we get list with 1 items
        """
        {"_items": [
            {"_id": "one", "type": "text", "versioncreated": "__now__"}
        ]}
        """

        When we patch "/archive/one"
        """
        {"headline": "foo"}
        """
        And we get "links?where={"guid": "three"}"
        Then we get list with 1 items
        """
        {"_items": [
            {"headline": "foo"}
        ]}
        """
