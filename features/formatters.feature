Feature: Formatters

    @auth
    @notification
    Scenario: Get list of formatters
        When we get "/formatters"
        Then we get list with 1+ items
        """
        {"_items": [
          {"name": "NITFFormatter"},
          {"name": "NINJSFormatter"},
          {"name": "NewsML12Formatter"},
          {"name": "NewsMLG2Formatter"}
          ]}
        """

    @auth
    @notification
    Scenario: Get formatted story
      Given the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
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
      When we post to "/formatters"
      """
      {"article_id": "123", "formatter_name": "NINJSFormatter"}
      """
      Then we get response code 201