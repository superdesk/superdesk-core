
Feature: Content Filter

  @auth
  @vocabulary
  Scenario: Add a new content filter
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "anpa_category", "operator": "in", "value": "4"}]
    """

    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer-only"}]
    """
    Then we get latest
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"], "pf": ["#content_filters._id#"]}}], "name": "complex"}]
    """
    And we get "/content_filters"
    Then we get list with 2 items
    """
    {
      "_items":
        [
          {"name": "soccer-only"},
          {"name": "complex"}
        ]
    }
    """

  @auth
  @vocabulary @test
  Scenario: Add a new content filter without global filter value but with archived flag
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "anpa_category", "operator": "in", "value": "4"}]
    """

    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer"}]
    """
    And we get "/content_filters"
    Then we get list with 1 items
    """
    {
      "_items":
        [
          {"name": "soccer", "is_global": false, "is_archived_filter": false}
        ]
    }
    """
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}],
      "name": "soccer archived", "is_archived_filter": true}]
    """
    And we get "/content_filters"
    Then we get list with 2 items
    """
    {
      "_items":
        [
          {"name": "soccer", "is_global": false, "is_archived_filter": false},
          {"name": "soccer archived", "is_global": false, "is_archived_filter": true}
        ]
    }
    """

  @auth
  @vocabulary
  Scenario: Add a new content filter with the same name fails
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "anpa_category", "operator": "in", "value": "4"}]
    """

    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer"}]
    """
    Then we get latest
    When we post to "/content_filters"
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"], "pf": ["#content_filters._id#"]}}], "name": "soccer"}]
    """
    Then we get error 400
    """
    {"_status": "ERR", "_issues": {"name": {"unique": 1}}}
    """

  @auth
  @vocabulary
  Scenario: Deleting content filter referenced by other content filters fails
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "anpa_category", "operator": "in", "value": "4"}]
    """

    Then we get latest
    Given empty "content_filters"
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer"}]
    """
    Then we get latest
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"], "pf": ["#content_filters._id#"]}}], "name": "tennis"}]
    """
    When we delete content filter "soccer"
    Then we get error 400
    When we delete content filter "tennis"
    Then we get error 204

  @auth
  @vocabulary
  Scenario: Deleting content filter referenced by direct products for subscribers
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "anpa_category", "operator": "in", "value": "4"}]
    """
    Then we get latest

    Given empty "content_filters"
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer"}]
    """
    Then we get latest

    Given empty "subscribers"
    When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both",
        "content_filter": {
            "filter_id": "#content_filters._id#",
            "filter_type": "blocking"
        }
      }
      """
    And we post to "/subscribers" with success
    """
    {
        "name": "Subscriber Foo",
        "media_type": "media",
        "subscriber_type": "digital",
        "products": ["#products._id#"],
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "email": "foo@bar.com",
        "destinations": [{
            "name": "destination1",
            "format": "nitf",
            "delivery_type": "FTP",
            "config": {"ip":"127.0.0.1", "password": "xyz"}
        }]
    }
    """
    Then we get latest

    When we delete content filter "soccer"
    Then we get error 400

  @auth
  @vocabulary
  Scenario: Deleting content filter referenced by api products for subscribers
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "anpa_category", "operator": "in", "value": "4"}]
    """
    Then we get latest

    Given empty "content_filters"
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer"}]
    """
    Then we get latest

    Given empty "subscribers"
    When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both",
        "content_filter": {
            "filter_id": "#content_filters._id#",
            "filter_type": "blocking"
        }
      }
      """
    And we post to "/subscribers" with success
    """
    {
        "name": "Subscriber Foo",
        "media_type": "media",
        "subscriber_type": "digital",
        "api_products": ["#products._id#"],
        "sequence_num_settings":{"min" : 1, "max" : 10},
        "email": "foo@bar.com"
    }
    """
    Then we get latest
    When we delete content filter "soccer"
    Then we get error 400

  @auth
  @vocabulary
  Scenario: Deleting content filter referenced by routing schemes fails
    Given empty "filter_conditions"
    When we post to "/filter_conditions" with success
    """
    [{"name": "sport", "field": "anpa_category", "operator": "in", "value": "4"}]
    """
    Then we get latest

    Given empty "content_filters"
    When we post to "/content_filters" with success
    """
    [{"content_filter": [{"expression": {"fc": ["#filter_conditions._id#"]}}], "name": "soccer"}]
    """
    Then we get latest

    Given empty "routing_schemes"
    When we post to "/routing_schemes"
    """
    {
        "name": "routing scheme 1",
        "rules": [{
            "name": "Sports Rule",
            "filter": "#content_filters._id#",
            "actions": {
                "fetch": []
            }
        }]
    }
    """
    Then we get latest

    When we delete content filter "soccer"
    Then we get error 400

  @auth
  @vocabulary
  Scenario: Try to Add duplicate filter
    Given "filter_conditions"
    """
    [{"name": "sport", "field": "anpa_category", "operator": "in", "value": "4,1"}]
    """
    When we post to "/filter_conditions"
    """
    [{"name": "water", "field": "anpa_category", "operator": "in", "value": "1,4"}]
    """
    Then we get error 400

  @auth
  @vocabulary
  Scenario: Try to Add none duplicate filter
    Given "filter_conditions"
    """
    [{"name": "sport", "field": "anpa_category", "operator": "in", "value": "AAP"}]
    """
    When we post to "/filter_conditions" with success
    """
    [{"name": "water", "field": "anpa_category", "operator": "in", "value": "PAA"}]
    """
    And we get "/filter_conditions"
    Then we get list with 2 items

  @auth
  @vocabulary
  Scenario: Update allowed fields on vocabulary add/delete
    Given empty "filter_conditions"
    When we post to "vocabularies" with success
    """
    [{"_id": "my_custom_field", "display_name": "My Custom Field", "type": "manageable", "field_type": "text", "items": []}]
    """
    And we post to "/filter_conditions" with success
    """
    [{"name": "water", "field": "my_custom_field", "operator": "eq", "value": "some_value"}]
    """
    And we get "/filter_conditions"
    Then we get list with 1 items

    When we delete "/vocabularies/my_custom_field"
    Then we get OK response
    When we post to "/filter_conditions"
    """
    [{"name": "other", "field": "my_custom_field", "operator": "eq", "value": "some_value"}]
    """
    Then we get error 400
    """
    {"_issues": {"field": "unallowed value my_custom_field"}, "_status": "ERR"}
    """
