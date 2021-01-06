Feature: Export

    @auth
    Scenario: Export a story with validate option OFF
      Given the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish"
        }
        ]
      """
      And "desks"
      """
      [{"name": "Sports", "content_expiry": 60}]
      """
      When we post to "/archive" with success
      """
      [{"guid": "123", "type": "text", "headline": "test",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
      """
      Then we get OK response
      When we post to "/export"
      """
      {"item_ids": ["#archive._id#"], "format_type": "NINJSFormatter", "validate": false}
      """
      Then we get response code 201
      Then we get new resource
      """
      {"failures": 0, "url": "__any_value__"}
      """
      When we get "#export.url#"
      Then we get response code 200
      And we get "Content-Disposition" header with "attachment; filename="export.zip"" type
      And we get "Content-Type" header with "application/zip" type

    @auth
    Scenario: Export a story with validate option OFF
      Given the "validators"
      """
        [
        {
            "schema": {"headline": {"required": true}},
            "type": "text",
            "act": "publish"
        }
        ]
      """
      And "desks"
      """
      [{"name": "Sports", "content_expiry": 60}]
      """
      When we post to "/archive" with success
      """
      [{"guid": "123", "type": "text", "headline": "test",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test",
        "body_html": "Test Document body"}]
      """
      Then we get OK response
      When we post to "/export"
      """
      {"item_ids": ["#archive._id#"], "format_type": "NINJSFormatter", "validate": true}
      """
      Then we get response code 201
      Then we get new resource
      """
      {"failures": 0, "url": "__any_value__"}
      """
      When we get "#export.url#"
      Then we get response code 200
      And we get "Content-Disposition" header with "attachment; filename="export.zip"" type
      And we get "Content-Type" header with "application/zip" type

    @auth
    Scenario: Fail to export an invalid story with validate option ON
      Given the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{"headline": {"required": true}}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{"guid": "123", "_current_version": 1, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "slugline": "test",
        "body_html": "Test Document body"}]
      """
      When we post to "/export"
      """
      {"item_ids": ["#archive._id#"], "format_type": "NINJSFormatter", "validate": true}
      """
      Then we get response code 201
      Then we get new resource
      """
      {"failures": 1, "url": "__none__"}
      """
