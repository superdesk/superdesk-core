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
        "name":"prod-1", "codes":"abc,xyz", "product_type": "both"
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
    {"content_filter":{"filter_id":"#content_filters._id#"}, "product_type": "direct"}
    """
    Then we get updated response
    """
    {"product_type": "direct", "content_filter":{"filter_id":"#content_filters._id#", "filter_type":"blocking"}}
    """
    When we patch "/products/#products._id#"
    """
    {"product_type": "api"}
    """
    Then we get error 400
    When we post to "/products" with success
    """
    {
      "name":"prod-2", "codes":"abc,xyz", "product_type": "api"
    }
    """
    Then we get OK response
    When we patch "/subscribers/#subscribers._id#"
    """
    {"api_products": ["#products._id#"]}
    """
    Then we get OK response
    When we patch "/products/#products._id#"
    """
    {"product_type": "both"}
    """
    Then we get OK response

  @auth
  @vocabulary
  Scenario: Create or Update a product with no product type
    When we post to "/products"
    """
    {
      "name":"prod-1", "codes":"abc,xyz"
    }
    """
    Then we get new resource
    """
    {"product_type": "both"}
    """
    When we post to "/products"
    """
    {
      "name":"prod-2", "codes":"abc,xyz", "product_type": "api"
    }
    """
    Then we get OK response
    When we patch "/products/#products._id#"
    """
    {"product_type": null}
    """
    Then we get error 400
    """
    {"_status": "ERR", "_issues": {"product_type": "null value not allowed"}}
    """

  @auth
  @vocabulary
  Scenario: Delete a product associated with subscriber fails
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
        "name":"prod-1", "codes":"abc,xyz", "product_type": "both"
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
    When we delete "/products/#products._id#"
    Then we get error 400
    """
    {"_message": "Product is used by the subscriber(s): News1", "_status": "ERR"}
    """
    When we post to "/products" with success
      """
      {
        "name":"prod-2", "codes":"abc,xyz", "product_type": "api"
      }
      """
    And we post to "/subscribers" with success
    """
    {
      "name":"News2","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10},
      "email": "test@test.com",
      "api_products": ["#products._id#"]
    }
    """
    When we delete "/products/#products._id#"
    Then we get error 400
    """
    {"_message": "Product is used by the subscriber(s): News2", "_status": "ERR"}
    """
    When we post to "/products" with success
      """
      {
        "name":"prod-3", "codes":"abc,xyz", "product_type": "api"
      }
      """
    When we delete "/products/#products._id#"
    Then we get OK response