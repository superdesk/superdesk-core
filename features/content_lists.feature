Feature: Content Lists

    @auth
    Scenario: Empty content lists
        Given empty "content_lists"
        When we get "/content_lists"
        Then we get list with 0 items

    @auth
    Scenario: Create a content list
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        And we get existing resource
        """
        {"name": "Breaking News", "type": "manual", "enabled": true}
        """

    @auth
    Scenario: Create a content list with all fields
        When we post to "/content_lists"
        """
        {
            "name": "Sports Feed",
            "type": "automatic",
            "description": "Automated sports content",
            "limit": 20,
            "cache_life_time": 300,
            "filters": {"category": "sport"},
            "enabled": false
        }
        """
        Then we get OK response
        And we get existing resource
        """
        {
            "name": "Sports Feed",
            "type": "automatic",
            "description": "Automated sports content",
            "limit": 20,
            "cache_life_time": 300,
            "enabled": false
        }
        """

    @auth
    Scenario: Create fails with empty name
        When we post to "/content_lists"
        """
        {"name": "", "type": "manual"}
        """
        Then we get error 400

    @auth
    Scenario: Create fails with invalid type
        When we post to "/content_lists"
        """
        {"name": "My List", "type": "invalid_type"}
        """
        Then we get error 400

    @auth
    Scenario: Update a content list
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we patch latest
        """
        {"name": "Updated Name", "description": "Now with description"}
        """
        Then we get updated response
        And we get existing resource
        """
        {"name": "Updated Name", "description": "Now with description"}
        """

    @auth
    Scenario: content_list_items_updated_at is server-managed
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we patch latest
        """
        {"content_list_items_updated_at": "2020-01-01T00:00:00+0000"}
        """
        Then we get updated response
        When we get "/content_lists/#content_lists._id#"
        Then we get existing resource
        """
        {"content_list_items_updated_at": "__no_value__"}
        """

    @auth
    Scenario: Delete a content list
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we delete latest
        Then we get deleted response

    @auth
    Scenario: Add item to content list via bulk patch
        Given an archive item "article-1"
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": null,
            "items": [
                {"action": "add", "contentId": "article-1", "position": 0}
            ]
        }
        """
        Then we get OK response
        When we get "/content_lists/#content_lists._id#/items"
        Then we get list with 1 items

    @auth
    Scenario: Move item in content list via bulk patch
        Given an archive item "article-1"
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": null,
            "items": [{"action": "add", "contentId": "article-1", "position": 0}]
        }
        """
        Then we get OK response
        And we store response as "content_lists"
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": "#content_lists.content_list_items_updated_at#",
            "items": [{"action": "move", "contentId": "article-1", "position": 5}]
        }
        """
        Then we get OK response
        When we get "/content_lists/#content_lists._id#/items"
        Then we get list with 1 items
        And we get existing resource
        """
        {"_items": [{"content": "article-1", "position": 5}]}
        """

    @auth
    Scenario: Delete item from content list via bulk patch
        Given an archive item "article-1"
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": null,
            "items": [{"action": "add", "contentId": "article-1", "position": 0}]
        }
        """
        Then we get OK response
        And we store response as "content_lists"
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": "#content_lists.content_list_items_updated_at#",
            "items": [{"action": "delete", "contentId": "article-1"}]
        }
        """
        Then we get OK response
        When we get "/content_lists/#content_lists._id#/items"
        Then we get list with 0 items

    @auth
    Scenario: Bulk patch with stale updatedAt returns 409
        Given an archive item "article-1"
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": null,
            "items": [{"action": "add", "contentId": "article-1", "position": 0}]
        }
        """
        Then we get OK response
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": "2000-01-01T00:00:00+0000",
            "items": [{"action": "add", "contentId": "article-1", "position": 1}]
        }
        """
        Then we get error 409

    @auth
    Scenario: Bulk patch without items field returns 400
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {"updatedAt": null}
        """
        Then we get error 400

    @auth
    Scenario: Bulk patch without updatedAt field returns 400
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {"items": []}
        """
        Then we get error 400

    @auth
    Scenario: Deleting a content list cascades to its items
        Given an archive item "article-1"
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": null,
            "items": [{"action": "add", "contentId": "article-1", "position": 0}]
        }
        """
        Then we get OK response
        When we get "/content_lists/#content_lists._id#/items"
        Then we get list with 1 items
        When we delete "/content_lists/#content_lists._id#"
        Then we get deleted response
        When we get "/content_lists/#content_lists._id#"
        Then we get response code 404
