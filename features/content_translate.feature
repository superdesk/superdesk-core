Feature: Translate Content

    @auth
    Scenario: Translate content item
      Given "archive"
      """
      [{"type":"text", "headline": "test1", "guid": "123", "original_creator": "abc", "state": "draft",  "language": "en-CA", "body_html": "$10", "firstcreated": "2018-01-01T01:01:01+0000"}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """

      When we post to "/archive/translate"
      """
      {"guid": "123", "language": "en-AU"}
      """
      And we get "/archive/#archive._id#"
      Then we get existing resource
      """
      {"translation_id": "123", "translations": ["#translate._id#"]}
      """

      When we get "/archive/#translate._id#"
      Then we get existing resource
      """
      {"type":"text", "headline": "test1", "state": "draft", "sign_off": "abc", "language": "en-AU", "body_html": "$10 (CAD 20)", "translated_from": "123", "translation_id": "123", "firstcreated": "__now__"}
      """

      When we post to "/archive/translate"
      """
      {"guid": "#translate._id#", "language": "de"}
      """
      And we get "/archive/#translate._id#"
      Then we get existing resource
      """
      {"language": "de", "translation_id": "123", "translations": "__none__"}
      """

      When we post to "/archive/translate"
      """
      {"guid": "123", "language": "en-AU"}
      """
      And we get "/archive/#translate._id#"
      Then we get existing resource
      """
      {"language": "en-AU", "translation_id": "123", "translated_from": "123", "translations": "__none__"}
      """

      When we post to "/archive/#translate._id#/duplicate"
      """
      {"desk": "#desks._id#", "type": "archive"}
      """
      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      {"translation_id": "__none__", "translations": "__none__", "translated_from": "__none__"}
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
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
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
      When we get "/published"
      Then we get list with 1 items
      """
      {"_items": [
        {"translation_id": "123", "translations": ["#translate._id#"]}
      ]}
      """

    @auth
    Scenario: Translate package
      Given "desks"
      """
      [{"name": "test"}]
      """
      Given "archive"
      """
      [
        {"type": "text", "headline": "text-item", "guid": "text-item", "state": "submitted", "language": "en", "original_creator": "#CONTEXT_USER_ID#"},
        {"type": "picture", "headline": "picture-item", "guid": "picture-item", "state": "submitted", "language": "en", "original_creator": "#CONTEXT_USER_ID#"}
      ]
      """

      When we post to "archive"
      """
      {
        "type": "composite", "headline": "package", "guid": "package", "language": "en", "groups": [
          {"id": "root", "refs": [{"idRef": "main"}]},
          {"id": "main", "refs": [
            {"residRef": "text-item"},
            {"residRef": "picture-item"}
          ]}
        ],
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}
      }
      """
      Then we get new resource
      When we post to "/archive/translate"
      """
      {"guid": "package", "language": "de", "desk": "#desks._id#"}
      """
  
      When we get "/archive/#translate._id#"
      Then we get existing resource
      """
      {"translated_from": "package", "operation": "translate", "task": {"stage": "#desks.working_stage#"}}
      """
      And we get package items
      """
      [
        {"type": "text", "language": "de", "translated_from": "text-item"},
        {"type": "picture", "language": "de", "translated_from": "picture-item"}
      ]
      """
