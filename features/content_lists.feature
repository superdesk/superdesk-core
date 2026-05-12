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
    Scenario: Moving an item shifts other items to keep positions unique
        Given an archive item "article-a"
        And an archive item "article-b"
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
                {"action": "add", "contentId": "article-a", "position": 0},
                {"action": "add", "contentId": "article-b", "position": 1}
            ]
        }
        """
        Then we get OK response
        And we store response as "content_lists"
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": "#content_lists.content_list_items_updated_at#",
            "items": [{"action": "move", "contentId": "article-b", "position": 0}]
        }
        """
        Then we get OK response
        When we get "/content_lists/#content_lists._id#/items?sort=position"
        Then we get list with 2 items
        And we get existing resource
        """
        {"_items": [
            {"content": "article-b", "position": 0},
            {"content": "article-a", "position": 1}
        ]}
        """

    @auth
    Scenario: Adding an item at an occupied position shifts the existing items down
        Given an archive item "article-a"
        And an archive item "article-b"
        And an archive item "article-c"
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
                {"action": "add", "contentId": "article-a", "position": 0},
                {"action": "add", "contentId": "article-b", "position": 1}
            ]
        }
        """
        Then we get OK response
        And we store response as "content_lists"
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": "#content_lists.content_list_items_updated_at#",
            "items": [{"action": "add", "contentId": "article-c", "position": 0}]
        }
        """
        Then we get OK response
        When we get "/content_lists/#content_lists._id#/items?sort=position"
        Then we get list with 3 items
        And we get existing resource
        """
        {"_items": [
            {"content": "article-c", "position": 0},
            {"content": "article-a", "position": 1},
            {"content": "article-b", "position": 2}
        ]}
        """

    @auth
    Scenario: Moving an item to a higher position shifts items in between
        Given an archive item "article-a"
        And an archive item "article-b"
        And an archive item "article-c"
        And an archive item "article-d"
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
                {"action": "add", "contentId": "article-a", "position": 0},
                {"action": "add", "contentId": "article-b", "position": 1},
                {"action": "add", "contentId": "article-c", "position": 2},
                {"action": "add", "contentId": "article-d", "position": 3}
            ]
        }
        """
        Then we get OK response
        And we store response as "content_lists"
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": "#content_lists.content_list_items_updated_at#",
            "items": [{"action": "move", "contentId": "article-a", "position": 2}]
        }
        """
        Then we get OK response
        When we get "/content_lists/#content_lists._id#/items?sort=position"
        Then we get list with 4 items
        And we get existing resource
        """
        {"_items": [
            {"content": "article-b", "position": 0},
            {"content": "article-c", "position": 1},
            {"content": "article-a", "position": 2},
            {"content": "article-d", "position": 3}
        ]}
        """

    @auth
    Scenario: Deleting an item shifts the items after it up
        Given an archive item "article-a"
        And an archive item "article-b"
        And an archive item "article-c"
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
                {"action": "add", "contentId": "article-a", "position": 0},
                {"action": "add", "contentId": "article-b", "position": 1},
                {"action": "add", "contentId": "article-c", "position": 2}
            ]
        }
        """
        Then we get OK response
        And we store response as "content_lists"
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": "#content_lists.content_list_items_updated_at#",
            "items": [{"action": "delete", "contentId": "article-a"}]
        }
        """
        Then we get OK response
        When we get "/content_lists/#content_lists._id#/items?sort=position"
        Then we get list with 2 items
        And we get existing resource
        """
        {"_items": [
            {"content": "article-b", "position": 0},
            {"content": "article-c", "position": 1}
        ]}
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
