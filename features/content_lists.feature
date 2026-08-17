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
    Scenario: Move action toggles sticky flag on an item
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
        When we get "/content_lists/#content_lists._id#/items"
        Then we get existing resource
        """
        {"_items": [{"content": "article-1", "position": 0, "sticky": false}]}
        """
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": "#content_lists.content_list_items_updated_at#",
            "items": [{"action": "move", "contentId": "article-1", "position": 3, "sticky": true}]
        }
        """
        Then we get OK response
        And we store response as "content_lists"
        When we get "/content_lists/#content_lists._id#/items"
        Then we get existing resource
        """
        {"_items": [{"content": "article-1", "position": 3, "sticky": true}]}
        """
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": "#content_lists.content_list_items_updated_at#",
            "items": [{"action": "move", "contentId": "article-1", "position": 2, "sticky": false}]
        }
        """
        Then we get OK response
        When we get "/content_lists/#content_lists._id#/items"
        Then we get existing resource
        """
        {"_items": [{"content": "article-1", "position": 2, "sticky": false}]}
        """

    @auth
    Scenario: Move action preserves sticky flag when not provided
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
            "items": [{"action": "add", "contentId": "article-1", "position": 0, "sticky": true}]
        }
        """
        Then we get OK response
        And we store response as "content_lists"
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": "#content_lists.content_list_items_updated_at#",
            "items": [{"action": "move", "contentId": "article-1", "position": 4}]
        }
        """
        Then we get OK response
        When we get "/content_lists/#content_lists._id#/items"
        Then we get existing resource
        """
        {"_items": [{"content": "article-1", "position": 4, "sticky": true}]}
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
    Scenario: Bulk patch without updatedAt field succeeds on a fresh list
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {"items": []}
        """
        Then we get OK response

    @auth
    Scenario: Bulk patch on an unknown list returns 404
        When we bulk patch items for "/content_lists/000000000000000000000000/items"
        """
        {"updatedAt": null, "items": []}
        """
        Then we get error 404

    @auth
    Scenario: Adding content already in the list is rejected as a duplicate
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
            "items": [{"action": "add", "contentId": "article-1", "position": 1}]
        }
        """
        Then we get error 400
        """
        {"_message": "Content list cannot be saved because it contains duplicated items"}
        """
        When we get "/content_lists/#content_lists._id#/items"
        Then we get list with 1 items

    @auth
    Scenario: A batch with a duplicate add is rejected without applying any change
        Given an archive item "article-1"
        And an archive item "article-2"
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
                {"action": "add", "contentId": "article-1", "position": 0},
                {"action": "add", "contentId": "article-2", "position": 1},
                {"action": "add", "contentId": "article-2", "position": 2}
            ]
        }
        """
        Then we get error 400
        """
        {"_message": "Content list cannot be saved because it contains duplicated items"}
        """
        When we get "/content_lists/#content_lists._id#/items"
        Then we get list with 0 items

    @auth
    Scenario: Add then delete of content already in the list cancels out
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
            "items": [
                {"action": "add", "contentId": "article-1", "position": 2},
                {"action": "delete", "contentId": "article-1"}
            ]
        }
        """
        Then we get OK response
        When we get "/content_lists/#content_lists._id#/items"
        Then we get list with 1 items
        And we get existing resource
        """
        {"_items": [{"content": "article-1", "position": 0}]}
        """

    @auth
    Scenario: Delete and re-add the same content in one batch
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
            "items": [
                {"action": "delete", "contentId": "article-1"},
                {"action": "add", "contentId": "article-1", "position": 2, "sticky": true}
            ]
        }
        """
        Then we get OK response
        When we get "/content_lists/#content_lists._id#/items"
        Then we get existing resource
        """
        {"_items": [{"content": "article-1", "position": 2, "sticky": true}]}
        """

    @auth
    Scenario: Items response includes article content
        Given an archive item "article-1" with data
        """
        {
            "headline": "Hello",
            "state": "published",
            "body_html": "<p><img src=\"https://cdn.example.com/pic.jpg\"></p>"
        }
        """
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
        Then we get existing resource
        """
        {"_items": [{
            "content": "article-1",
            "article_content": {
                "title": "Hello",
                "state": "published",
                "thumbnail": "https://cdn.example.com/pic.jpg"
            }
        }]}
        """

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

    @auth
    Scenario: Empty content list webhooks
        Given empty "content_list_webhooks"
        When we get "/content_list_webhooks"
        Then we get list with 0 items

    @auth
    Scenario: Create a webhook
        When we post to "/content_list_webhooks"
        """
        {"url": "https://example.com/hook"}
        """
        Then we get OK response
        And we get existing resource
        """
        {"url": "https://example.com/hook", "enabled": true, "excluded_lists": []}
        """

    @auth
    Scenario: Create a webhook with all fields
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        And we store response as "content_lists"
        When we post to "/content_list_webhooks"
        """
        {
            "url": "https://example.com/hook",
            "name": "My hook",
            "enabled": false,
            "excluded_lists": ["#content_lists._id#"]
        }
        """
        Then we get OK response
        And we get existing resource
        """
        {
            "url": "https://example.com/hook",
            "name": "My hook",
            "enabled": false,
            "excluded_lists": ["#content_lists._id#"]
        }
        """

    @auth
    Scenario: Create webhook fails with empty url
        When we post to "/content_list_webhooks"
        """
        {"url": ""}
        """
        Then we get error 400

    @auth
    Scenario: Create webhook fails with a non-http url
        When we post to "/content_list_webhooks"
        """
        {"url": "not-a-url"}
        """
        Then we get error 400
        When we post to "/content_list_webhooks"
        """
        {"url": "ftp://example.com/hook"}
        """
        Then we get error 400

    @auth
    Scenario: Webhook url is stored in canonical form
        When we post to "/content_list_webhooks"
        """
        {"url": "https://example.com"}
        """
        Then we get OK response
        And we get existing resource
        """
        {"url": "https://example.com/"}
        """

    @auth
    Scenario: Webhooks require the content lists privilege
        When we login as user "plain" with password "barbar" and user type "user"
        And we get "/content_lists"
        Then we get list with 0 items
        When we get "/content_list_webhooks"
        Then we get response code 403

    @auth
    Scenario: Update a webhook
        When we post to "/content_list_webhooks"
        """
        {"url": "https://example.com/hook"}
        """
        Then we get OK response
        When we patch latest
        """
        {"enabled": false}
        """
        Then we get updated response
        And we get existing resource
        """
        {"url": "https://example.com/hook", "enabled": false}
        """

    @auth
    Scenario: Delete a webhook
        When we post to "/content_list_webhooks"
        """
        {"url": "https://example.com/hook"}
        """
        Then we get OK response
        When we delete latest
        Then we get deleted response

    @auth
    Scenario: Updating items delivers a webhook
        Given an archive item "article-1"
        And a webhook endpoint at "https://hooks.example.com/one"
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we reset webhook deliveries
        And we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": null,
            "items": [{"action": "add", "contentId": "article-1", "position": 0}]
        }
        """
        Then we get OK response
        And we delivered 1 webhook
        """
        [{"event": "content_list:items_updated", "list_id": "#content_lists._id#"}]
        """

    @auth
    Scenario: Creating a list delivers a webhook
        Given a webhook endpoint at "https://hooks.example.com/one"
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        And we delivered 1 webhook
        """
        [{"event": "content_list:created", "list_id": "#content_lists._id#"}]
        """

    @auth
    Scenario: Updating a list delivers a webhook
        Given a webhook endpoint at "https://hooks.example.com/one"
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we reset webhook deliveries
        And we patch latest
        """
        {"name": "Updated Name"}
        """
        Then we get updated response
        And we delivered 1 webhook
        """
        [{"event": "content_list:updated", "list_id": "#content_lists._id#"}]
        """

    @auth
    Scenario: Deleting a list delivers a webhook
        Given a webhook endpoint at "https://hooks.example.com/one"
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we reset webhook deliveries
        And we delete latest
        Then we get deleted response
        And we delivered 1 webhook
        """
        [{"event": "content_list:deleted", "list_id": "#content_lists._id#"}]
        """

    @auth
    Scenario: A disabled webhook is not delivered to
        Given a mocked http endpoint at "https://hooks.example.com/one"
        When we post to "/content_list_webhooks"
        """
        {"url": "https://hooks.example.com/one", "enabled": false}
        """
        Then we get OK response
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        And we delivered 0 webhooks

    @auth
    Scenario: A webhook excluding a list is skipped while others still receive
        Given a mocked http endpoint at "https://hooks.example.com/one"
        And a mocked http endpoint at "https://hooks.example.com/two"
        When we post to "/content_lists"
        """
        {"name": "Breaking News", "type": "manual"}
        """
        Then we get OK response
        When we post to "/content_list_webhooks"
        """
        {"url": "https://hooks.example.com/one", "excluded_lists": ["#content_lists._id#"]}
        """
        Then we get OK response
        When we post to "/content_list_webhooks"
        """
        {"url": "https://hooks.example.com/two"}
        """
        Then we get OK response
        When we reset webhook deliveries
        And we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {"updatedAt": null, "items": []}
        """
        Then we get OK response
        And we delivered 1 webhook to "https://hooks.example.com/two"
        """
        [{"event": "content_list:items_updated", "list_id": "#content_lists._id#"}]
        """
        And we delivered 0 webhooks to "https://hooks.example.com/one"

    @auth
    Scenario: A rejected bulk patch delivers no webhook
        Given an archive item "article-1"
        And a webhook endpoint at "https://hooks.example.com/one"
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
        When we reset webhook deliveries
        And we bulk patch items for "/content_lists/#content_lists._id#/items"
        """
        {
            "updatedAt": "2000-01-01T00:00:00+0000",
            "items": [{"action": "add", "contentId": "article-1", "position": 1}]
        }
        """
        Then we get error 409
        And we delivered 0 webhooks

    @auth
    Scenario: A failing webhook endpoint does not fail the request
        Given an archive item "article-1"
        And a failing webhook endpoint at "https://hooks.example.com/broken"
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
