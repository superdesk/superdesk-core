@wip
Feature: Unpublish content
    
    @auth
    Scenario: Unpublish single item
      Given "desks"
      """
      [{"name": "Sports", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 0, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test", "type": "text",
        "body_html": "<p>Test Document body</p>\n<p>with a \"quote\"</p>"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}],
        "api_products": ["#products._id#"]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we enqueue published
      Then we assert the content api item "123" is published to subscriber "#subscribers._id#"
      When we get "/items/123"
      
      And we publish "#archive._id#" with "unpublish" type and "unpublished" state
      Then we get OK response
      And we get existing resource
      """
      {"state": "unpublished", "pubstatus": "canceled"}
      """
      When we enqueue published
      Then we assert the content api item "123" is published to subscriber "#subscribers._id#"

      When we get "/publish_queue"
      Then we get list with 4 items
      """
      {
        "_items": [
          {"publishing_action": "unpublished"},
          {"publishing_action": "unpublished"},
          {"publishing_action": "published"},
          {"publishing_action": "published"}
        ]
      }
      """

      When we patch "/archive/#archive._id#"
      """
      {"state": "in_progress"}
      """
      Then we get OK response

      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response