Feature: Content Filter Tests

  @auth
  @vocabulary
  Scenario: Test existing content filter to get matching articles
    Given empty "archive"
    When we post to "/archive"
    """
    [{"urgency": 1}]
    """
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "urgency", "operator": "in", "value": "1,2,3"}]
    """
    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer-only"}]
    """
    When we post to "/content_filters/test"
    """
    [{"return_matching": true, "filter_id": "#content_filters._id#"}]
    """
    Then we get existing resource
    """
    {
      "match_results": [{"urgency": 1}]
    }
    """

  @auth
  @vocabulary
  Scenario: Test in-memory content filter to get matching articles
    Given empty "archive"
    When we post to "/archive"
    """
    [{"urgency": 1}]
    """
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "urgency", "operator": "in", "value": "1,2,3"}]
    """
    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters/test"
    """
    [{"return_matching": true, "filter": {"content_filter": [{"expression" : {"fc" : ["#filter_conditions._id#"]}}]}}]
    """
    Then we get existing resource
    """
    {
      "match_results": [{"urgency": 1}]
    }
    """

  @auth
  @vocabulary
  Scenario: Test content filter to get non-matching articles
    Given empty "archive"
    When we post to "/archive"
    """
    [{"urgency": 1}]
    """
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "urgency", "operator": "in", "value": "2,3"}]
    """
    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer-only"}]
    """
    When we post to "/content_filters/test"
    """
    [{"return_matching": false, "filter_id": "#content_filters._id#"}]
    """
    Then we get existing resource
    """
    {
      "match_results": [{"urgency": 1}]
    }
    """

  @auth
  @vocabulary
  Scenario: Test in-memory content filter to get non-matching articles
    Given empty "archive"
    When we post to "/archive"
    """
    [{"urgency": 5}]
    """
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "urgency", "operator": "in", "value": "1,2,3"}]
    """
    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters/test"
    """
    [{"return_matching": false, "filter": {"content_filter": [{"expression" : {"fc" : ["#filter_conditions._id#"]}}]}}]
    """
    Then we get existing resource
    """
    {
      "match_results": [{"urgency": 5}]
    }
    """

  @auth
  @vocabulary
  Scenario: Test a single article
    Given empty "archive"
    When we post to "/archive"
    """
    [{"urgency": 1}]
    """
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "urgency", "operator": "in", "value": "1,2,3"}]
    """
    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer-only"}]
    """
    When we post to "/content_filters/test"
    """
    [{"filter_id": "#content_filters._id#", "article_id":"#archive._id#"}]
    """
    Then we get existing resource
    """
    {
      "match_results": true
    }
    """

  @auth
  @vocabulary
  Scenario: Test in-memory content filter to single article
    Given empty "archive"
    When we post to "/archive"
    """
    [{"urgency": 5}]
    """
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "urgency", "operator": "in", "value": "1,2,3"}]
    """
    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters/test"
    """
    [{"filter": {"content_filter": [{"expression" : {"fc" : ["#filter_conditions._id#"]}}]},
      "article_id": "#archive._id#"}]
    """
    Then we get existing resource
    """
    {
      "match_results": false
    }
    """

  @auth
  @vocabulary
  Scenario: Test single article from ingest
    Given "ingest"
    """
    [{"guid": 1, "_id": 1, "urgency": 1}]
    """
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "urgency", "operator": "in", "value": "1,2,3"}]
    """
    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer-only"}]
    """
    When we post to "/content_filters/test"
    """
    [{"filter_id": "#content_filters._id#", "article_id":"1"}]
    """
    Then we get existing resource
    """
    {
      "match_results": true
    }
    """

  @auth
  Scenario: Test filtering with custom cv
    When we post to "archive" with success
    """
    {"guid": "foo", "headline": "foo", "subject": [], "type": "text", "version": 1}
    """
    When we post to "vocabularies" with success
    """
    {"_id": "categories", "items": [{"name": "National", "qcode": "a", "is_active": true}], "type": "manageable", "display_name": "Cat"}
    """
    When we post to "/filter_conditions" with success
    """
    {"name": "cat", "field": "categories", "operator": "in", "value": "a"}
    """

    When we post to "/content_filters/test"
    """
    {
      "article_id": "#archive._id#",
      "filter": {
        "name": "test",
        "content_filter": [
          {"expression": {"fc": ["#filter_conditions._id#"]}}
        ]
      }
    }
    """
    Then we get existing resource
    """
    {"match_results": false}
    """

    When we patch "/archive/#archive._id#"
    """
    {"subject": [{"name": "national", "qcode": "a", "scheme": "categories"}]}
    """
    When we post to "/content_filters/test"
    """
    {
      "article_id": "#archive._id#",
      "filter": {
        "name": "test",
        "content_filter": [
          {"expression": {"fc": ["#filter_conditions._id#"]}}
        ]
      }
    }
    """
    Then we get existing resource
    """
    {"match_results": true}
    """

  @auth
  @vocabulary
  Scenario: Test in-memory content filter using exists
    Given empty "archive"
    When we post to "/archive"
    """
    [{"associations": {"featuremedia": {"_id": "12345"}}}]
    """
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "test", "field": "featuremedia", "operator": "exists", "value": "True"}]
    """
    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters/test"
    """
    [{"filter": {"content_filter": [{"expression" : {"fc" : ["#filter_conditions._id#"]}}]},
      "article_id": "#archive._id#"}]
    """
    Then we get existing resource
    """
    {
      "match_results": true
    }
    """

  @auth
  @vocabulary
  Scenario: Test in-memory content filter using exists false
    Given empty "archive"
    When we post to "/archive"
    """
    [{"associations": {"featuremedia": {"_id": "12345"}}}]
    """
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "test", "field": "featuremedia", "operator": "exists", "value": "False"}]
    """
    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters/test"
    """
    [{"filter": {"content_filter": [{"expression" : {"fc" : ["#filter_conditions._id#"]}}]},
      "article_id": "#archive._id#"}]
    """
    Then we get existing resource
    """
    {
      "match_results": false
    }
    """


  @auth
  @vocabulary
  Scenario: Test in-memory content filter does not exists
    Given empty "archive"
    When we post to "/archive"
    """
    [{"associations": {}}]
    """
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "test", "field": "featuremedia", "operator": "exists", "value": "True"}]
    """
    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters/test"
    """
    [{"filter": {"content_filter": [{"expression" : {"fc" : ["#filter_conditions._id#"]}}]},
      "article_id": "#archive._id#"}]
    """
    Then we get existing resource
    """
    {
      "match_results": false
    }
    """