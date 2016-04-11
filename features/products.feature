Feature: Products

    @auth
  @vocabulary
  Scenario: Update a product with publish filter
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
    Given empty "subscribers"
    When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
      }
      """
    And we post to "/subscribers" with success
    """
    {
      "name":"News1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10},
      "email": "test@test.com",
      "products": ["#products._id#"],
      "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP","config":{"ip":"144.122.244.55","password":"xyz"}}]
    }
    """
    When we patch "/products/#products._id#"
    """
    {"content_filter":{"filter_id":"#content_filters._id#"}}
    """
    Then we get updated response
    """
    {"content_filter":{"filter_id":"#content_filters._id#", "filter_type":"blocking"}}
    """