Feature: Keywords

    @alchemy
    @auth
    Scenario: Get the list of keywords for a content item
        When we post to "/keywords"
        """
        {
         "text": "ATHENS (Reuters) - Greece is willing to support Turkey over migration but will not compromise on national issues, Prime Minister Alexis Tsipras said on Friday after attending an EU Summit in Brussels. EU leaders agreed overnight to offer Ankara cash, easier visa terms and a re-energized consideration of Turkey's membership bid."
        }
        """
        Then we get existing resource
        """
        {"_id": 0,
         "keywords": [{"relevance": "0.943564", "text": "Prime Minister Alexis Tsipras"},
                      {"relevance": "0.915151", "text": "EU"},
                      {"relevance": "0.775952", "text": "Turkey"},
                      {"relevance": "0.542216", "text": "Reuters"},
                      {"relevance": "0.490861", "text": "ATHENS"},
                      {"relevance": "0.47575", "text": "Brussels"},
                      {"relevance": "0.458178", "text": "Ankara"},
                      {"relevance": "0.455677", "text": "Greece"}
                   ]
         }
        """

    @auth
    @notification
    Scenario: Save keywords on item publish
    Given config update
    """
    {"KEYWORDS_ADD_MISSING_ON_PUBLISH": true}
    """

    Given "archive"
    """
    [
        {"_id": "test", "guid": "test", "state": "in_progress", "headline": "foo", "keywords": ["Foo", "bar"]}
    ]
    """
    When we publish "#archive._id#" with "publish" type and "published" state
    Then we get OK response
    And we get notifications
    """
    [{"event": "vocabularies:created", "extra": {"vocabulary": "Keywords", "user": "#CONTEXT_USER_ID#"}}]
    """

    When we get "vocabularies/keywords"
    Then we get existing resource
    """
    {"items": [
        {"name": "Foo", "qcode": "Foo"},
        {"name": "bar", "qcode": "bar"}
    ], "unique_field": "name"}
    """

    Given "archive"
    """
    [
        {"_id": "test2", "guid": "test2", "state": "in_progress", "headline": "bar", "keywords": ["bar", "baz"]}
    ]
    """
    When we publish "#archive._id#" with "publish" type and "published" state
    And we get "vocabularies/keywords"
    Then we get existing resource
    """
    {"items": [
        {"name": "Foo", "qcode": "Foo"},
        {"name": "bar", "qcode": "bar"},
        {"name": "baz", "qcode": "baz"}
    ], "unique_field": "name"}
    """
    And we get notifications
    """
    [{"event": "vocabularies:updated", "extra": {"vocabulary": "Keywords", "user": "#CONTEXT_USER_ID#"}}]
    """
