Feature: Copy Content in Personal Workspace

    @auth
    Scenario: Copy content in personal workspace and validate metadata set by API
      Given "archive"
      """
      [{"type":"text", "headline": "test1", "guid": "123", "original_creator": "abc", "state": "draft"}]
      """
      When we patch given
      """
      {"headline": "test2"}
      """
      And we patch latest
      """
      {"headline": "test3"}
      """
      Then we get updated response
      """
      {"headline": "test3", "sign_off": "abc"}
      """
      When we post to "/archive/123/copy"
      """
      {}
      """
      When we get "/archive/#copy._id#"
      Then we get existing resource
      """
      {"state": "draft", "sign_off": "abc"}
      """
      And we get version 4
      When we get "/archive/#copy._id#?version=all"
      Then we get list with 4 items
      When we get "/archive/"
      Then we get list with 2 items

    @auth
    Scenario: Copy item in a desk will show it in personal
      Given "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{  "type":"text", "headline": "test1", "guid": "123", "original_creator": "abc", "state": "submitted",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}]
      """
      When we post to "/archive/123/copy"
      """
      {}
      """
      Then we get new resource
      When we get "/archive/"
      Then we get list with 2 items
      """
      {"_items": [
        {"original_creator": "#CONTEXT_USER_ID#", "task": "__empty__", "family_id": "123"}
      ]}
      """
