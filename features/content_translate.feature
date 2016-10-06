Feature: Translate Content

    @auth
    Scenario: Translate content item
      Given "archive"
      """
      [{"type":"text", "headline": "test1", "guid": "123", "original_creator": "abc", "state": "draft"}]
      """
      When we post to "/archive/translate"
      """
      {"guid": "123", "language": "de"}
      """
      When we get "/archive/#translate._id#"
      Then we get existing resource
      """
      {"type":"text", "headline": "test1", "state": "draft", "sign_off": "abc", "language": "de"}
      """

    @auth
    Scenario: Translate published content item 
      Given empty "ingest"
      And the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
       {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{  "type":"text", "headline": "test1", "guid": "123", "original_creator": "#CONTEXT_USER_ID#",
          "state": "submitted", "source": "REUTERS", "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
      """
      When we patch "/archive/123"
      """
      {"publish_schedule":"#DATE+1#"}
      """

      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we post to "/archive/translate"
      """
      {"guid": "123", "language": "de"}
      """
      When we get "/archive/#translate._id#"
      Then we get existing resource
      """
      {"type":"text", "headline": "test1", "state": "submitted", "sign_off": "abc", "language": "de", "source": "AAP", 
       "subject":[{"qcode": "17004000", "name": "Statistics"}], "body_html": "Test Document body"}
      """
