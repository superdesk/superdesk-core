Feature: Content Expiry Not Published Items

  Background: Setup data required to test not published items
    Given "desks"
    """
    [{"name": "Sports", "content_expiry": 60}]
    """
    When we post to "/archive" with success
    """
    [{"guid": "123", "type": "text", "headline": "test", "state": "fetched",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body"}]
    """
    Then we get OK response
    And we get existing resource
    """
    {"_current_version": 1, "state": "fetched", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
    """

  @auth
  @notification
  Scenario: Item on a desk and not part of any package is expired .
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 1 items
    """
    {"_items": [
      {"version": 1, "operation": "create"}
    ]}
    """
    When we expire items
    """
    ["#archive._id#"]
    """
    And we get "archive/123"
    Then we get error 404
    When we get "archive/123?versions=all"
    Then we get error 404
    When we get "/archive_history?where=item_id==%22123%22"
    Then we get list with 0 items
    And we get notifications
    """
    [
        {
            "event": "item:expired",
            "extra": {
                "items": {"123": 1}
            }
        }
    ]
    """

  @auth
  Scenario: Item on a desk is spiked and expired.
    When we spike "123"
    Then we get OK response
    When we expire items
    """
    ["123"]
    """
    And we get "archive/123"
    Then we get error 404
    When we get "archive/123?versions=all"
    Then we get error 404

  @auth
  Scenario: Item in a package is expired.
    When we post to "/archive" with "package" and success
    """
    {"guid": "package", "type": "composite", "headline": "test package", "state": "fetched",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Package",
      "groups": [
                {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                {
                    "id": "main",
                    "refs": [
                        {
                            "headline": "Test Document body",
                            "residRef": "123",
                            "slugline": ""
                        }
                    ],
                    "role": "grpRole:Main"
                }
      ]
    }
    """
    And we get "archive"
    Then we get list with 2 items
    """
    {"_items": [
      {"_id": "123", "type": "text", "linked_in_packages": [{"package": "#package#"}], "_current_version": 1},
      {"_id": "#package#", "type": "composite", "_current_version": 1}
    ]}
    """
    When we expire items
    """
    ["#package#"]
    """
    And we get "archive"
    Then we get list with 2 items
    """
    {"_items": [
      {"_id": "123"}, {"_id": "package"}
    ]}
    """
    When we post to "/archive" with "package2" and success
    """
    {"guid": "package2", "type": "composite", "headline": "test package", "state": "fetched",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Package",
      "groups": [
                {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                {
                    "id": "main",
                    "refs": [
                        {
                            "headline": "Test Document body",
                            "residRef": "123",
                            "slugline": ""
                        }
                    ],
                    "role": "grpRole:Main"
                }
      ]
    }
    """
    When we expire items
    """
    ["123"]
    """
    And we get "archive"
    Then we get list with 3 items
    """
    {"_items": [
      {"_id": "123", "type": "text",
       "linked_in_packages": [{"package": "#package#"},{"package": "#package2#"}], "_current_version": 1},
      {"_id": "#package2#", "type": "composite", "_current_version": 1},
      {"_id": "#package#", "type": "composite", "_current_version": 1}
    ]}
    """
    When we expire items
    """
    ["#package2#"]
    """
    And we get "archive"
    Then we get list with 0 items



  @auth
  Scenario: Personal content is spiked and expired.
    When we post to "archive" with success
    """
    [{"guid": "456", "type": "text", "headline": "test", "state": "fetched",
      "task": {"user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body"}]
    """
    And we get "archive"
    Then we get list with 2 items
    """
    {"_items": [
      {"_id": "123"}, {"_id": "456"}
    ]}
    """
    When we spike "456"
    Then we get OK response
    When we expire items
    """
    ["456"]
    """
    And we get "archive/456"
    Then we get error 404
    When we get "archive/456?versions=all"
    Then we get error 404

  @auth
  Scenario: Personal content is expired but not spiked.
    When we post to "archive" with success
    """
    [{"guid": "456", "type": "text", "headline": "test", "state": "fetched",
      "task": {"user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body"}]
    """
    And we get "archive"
    Then we get list with 2 items
    """
    {"_items": [
      {"_id": "123"}, {"_id": "456"}
    ]}
    """
    When we expire items
    """
    ["456"]
    """
    And we get "archive/456"
    Then we get OK response
    When we get "archive/456?versions=all"
    Then we get OK response

  @auth
  Scenario: Content linked in planning does not expire.
    Given "assignments"
    """
    [{"_id": "123456", "planning": {}}]
    """
    When we post to "archive" with success
    """
    [{"guid": "456", "type": "text", "headline": "test", "state": "fetched",
      "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
      "subject":[{"qcode": "17004000", "name": "Statistics"}],
      "body_html": "Test Document body",
      "assignment_id": "123456"}]
    """
    And we get "archive"
    Then we get list with 2 items
    """
    {"_items": [
      {"_id": "123"}, {"_id": "456"}
    ]}
    """
    When we expire items
    """
    ["456"]
    """
    And we get "archive/456"
    Then we get OK response
    When we get "archive/456?versions=all"
    Then we get OK response