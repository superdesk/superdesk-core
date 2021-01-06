Feature: Subscribers

  @auth @notification
  Scenario: Add a new subscriber
    Given empty "subscribers"
    When we get "/subscribers"
    Then we get list with 0 items
    When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
    And we post to "/subscribers" with success
    """
    {
      "name":"News1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["#products._id#"],
      "codes": "xyz, abc",
      "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP","config":{"ip":"144.122.244.55","password":"xyz"}}]
    }
    """
    Then we get OK response
    Then we get notifications
    """
    [{"event": "subscriber:create", "extra": {"_id": ["#subscribers._id#"]}}]
    """
    When we get "/subscribers"
    Then we get list with 1 items
    """
    {"_items":[{"name":"News1", "is_targetable": true}]}
    """

  @auth
  Scenario: Create new subscriber with invalid product type.
    Given empty "subscribers"
    When we get "/subscribers"
    Then we get list with 0 items
    When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "direct"
      }
      """
    And we post to "/subscribers"
    """
    {
      "name":"News1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "api_products": ["#products._id#"],
      "codes": "xyz, abc"
    }
    """
    Then we get error 400
    When we patch "/products/#products._id#"
    """
    {"product_type": "api"}
    """
    Then we get OK response
    When we post to "/subscribers"
    """
    {
      "name":"News1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["#products._id#"],
      "codes": "xyz, abc"
    }
    """
    Then we get error 400


  @auth
  Scenario: Add a new subscriber without product succeeds
    Given empty "subscribers"
    When we get "/subscribers"
    Then we get list with 0 items
    When we post to "/subscribers"
    """
    {
      "name":"News1","media_type":"media", "subscriber_type": "digital",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "destinations":[{"name":"destination1","format": "nitf",
      "delivery_type":"FTP","config":{"ip":"144.122.244.55","password":"xyz"}}]
    }
    """
    Then we get response code 201


  @auth @notification
  Scenario: Update a subscriber
    Given empty "subscribers"
    When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
    And we post to "/subscribers"
    """
    {
      "name":"News1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["#products._id#"],
      "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP","config":{"ip":"144.122.244.55","password":"xyz"}}]
    }
    """
    Then we get OK response
    Then we get notifications
    """
    [{"event": "subscriber:create", "extra": {"_id": ["#subscribers._id#"]}}]
    """
    When we patch latest
    """
    {"destinations":[{"name":"destination2", "format": "nitf", "delivery_type":"email", "config":{"recipients":"abc@abc.com"}}]}
    """
    Then we get updated response
    """
    {"destinations":[{"name":"destination2", "format": "nitf", "delivery_type":"email", "config":{"recipients":"abc@abc.com"}}]}
    """
    Then we get notifications
    """
    [
     {"event": "subscriber:create", "extra": {"_id": ["#subscribers._id#"]}},
     {"event": "subscriber:update", "extra": {"_id": ["#subscribers._id#"]}}
    ]
    """

  @auth
  @vocabulary
  Scenario: Query subscribers by filter condition
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
        "name":"prod-1","codes":"abc,xyz",
        "content_filter": {"filter_id":"#content_filters._id#", "filter_type":"blocking"}, "product_type": "both"
      }
      """
    And we post to "/subscribers" with success
    """
    {
      "name":"News-Direct",
      "media_type":"media",
      "subscriber_type": "wire",
      "sequence_num_settings":{"min" : 1, "max" : 10},
      "email": "test@test.com",
      "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP","config":{"ip":"144.122.244.55","password":"xyz"}}],
      "products": ["#products._id#"]
    }
    """
    And we post to "/subscribers" with success
    """
    {
      "name":"News-API",
      "media_type":"media",
      "subscriber_type": "digital",
      "sequence_num_settings":{"min" : 1, "max" : 10},
      "email": "test@test.com",
      "api_products": ["#products._id#"]
    }
    """
    And we get "/subscribers?filter_condition={"field":"anpa_category", "operator":"in", "value":"4"}"
    Then we get list with 1 items
    """
    {"_items":[{
    "filter_conditions": [{"name": "sport"}],
    "content_filters": [{"name": "soccer-only"}],
    "products": [{"name": "prod-1"}],
    "selected_subscribers": [{"name":"News-Direct"}, {"name":"News-API"}]}]}
    """

  @auth
  Scenario: Deleting a Subscriber is not allowed
    Given empty "subscribers"
    When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
    And we post to "/subscribers"
    """
    {
      "name":"News1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["#products._id#"],
      "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP","config":{"ip":"144.122.244.55","password":"xyz"}}]
    }
    """
    When we delete latest
    Then we get error 405

  @auth
  Scenario: Creating a Subscriber should fail if there are no destinations
    Given empty "subscribers"
     When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
    And we post to "/subscribers"
    """
    {
      "name":"News1",
      "products": ["#products._id#"],
      "email": "test@test.com",
      "subscriber_type": "digital","media_type":"media", "sequence_num_settings":{"min" : 1, "max" : 10}
    }
    """
    Then we get error 400
    """
    {"_issues": {
      "destinations": {"required": 1},
      "api_products": {"required": 1}},
      "_status": "ERR"}
    """
    When we post to "/subscribers"
    """
    {
      "name":"News1", "subscriber_type": "digital","media_type":"media", "sequence_num_settings":{"min" : 1, "max" : 10},
      "email": "test@test.com",
      "products": ["#products._id#"],
      "destinations": []
    }
    """
    Then we get error 400
    """
    {"_issues": {"destinations": {"required": 1}}, "_status": "ERR"}
    """

  @auth
  Scenario: Creating a subscriber with api product only but no destinations.
    Given empty "subscribers"
    When we post to "/products" with success
    """
    {
      "name":"prod-1","codes":"abc,xyz", "product_type": "both"
    }
    """
    And we post to "/subscribers"
    """
    {
      "name":"News1",
      "email": "test@test.com",
      "subscriber_type": "digital","media_type":"media", "sequence_num_settings":{"min" : 1, "max" : 10},
      "api_products": ["#products._id#"]
    }
    """
    Then we get OK response
    When we patch "/subscribers/#subscribers._id#"
    """
    {"api_products": []}
    """
    Then we get error 400
    """
    {"_issues": {"validator exception": "400: At least one destination or one API Product should be specified"}, "_status": "ERR"}
    """
    When we patch "/subscribers/#subscribers._id#"
    """
    {"products": ["#products._id#"]}
    """
    Then we get error 400


  @auth
  Scenario: Updating a Subscriber with no destinations should fail
    Given empty "subscribers"
    When we get "/subscribers"
    Then we get list with 0 items
    When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
    And we post to "/subscribers" with success
    """
    {
      "name":"News1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["#products._id#"],
      "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP","config":{"ip":"144.122.244.55","password":"xyz"}}]
    }
    """
    And we get "/subscribers"
    Then we get list with 1 items
    """
    {"_items":[{"name":"News1"}]}
    """
    When we patch "/subscribers/#subscribers._id#"
    """
    {"destinations":[]}
    """
    Then we get error 400
    """
    {"_issues": {"validator exception": "400: At least one destination or one API Product should be specified"}, "_status": "ERR"}
    """

  @auth
  Scenario: Creating a Subscriber should fail when Mandatory properties are not passed for destinations
    Given empty "subscribers"
    When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
    And we post to "/subscribers"
    """
    {
      "name":"News1", "subscriber_type": "digital","media_type":"media", "sequence_num_settings":{"min" : 1, "max" : 10},
      "products": ["#products._id#"],
      "destinations":[{"name": ""}]
    }
    """
    Then we get error 400
    """
    {"_issues": {"destinations": {"0": {
                                        "name": "empty values not allowed",
                                        "format": {"required": 1},
                                        "delivery_type": {"required": 1}}}},
     "_status": "ERR"}
    """

  @auth
  Scenario: Creating a Subscriber with sequence number should fail if min value is less than or equal to 0
    Given empty "subscribers"
    When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
    And we post to "/subscribers"
    """
    {
      "name":"News1", "subscriber_type": "digital","media_type":"media", "sequence_num_settings":{"min" : 0, "max" : 10}, "email": "test@test.com",
      "products": ["#products._id#"],
      "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP","config":{"ip":"144.122.244.55","password":"xyz"}}]
    }
    """
    Then we get error 400
    """
    {"_issues": {"sequence_num_settings.min": 1}, "_message": "Value of Minimum in Sequence Number Settings should be greater than 0"}
    """

  @auth
  @notification
  Scenario: Update critical errors for subscriber 1
    Given empty "subscribers"
    When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
    And we post to "/subscribers" with success
    """
    {
      "name":"News1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["#products._id#"],
      "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP","config":{"ip":"144.122.244.55","password":"xyz"}}]
    }
    """
    When we patch "/subscribers/#subscribers._id#"
    """
    {"critical_errors":{"6000":true, "6001":true}}
    """
    Then we get updated response
    """
    {"critical_errors":{"6000":true, "6001":true}}
    """

  @auth
  @vocabulary
  @notification
  Scenario: Update critical errors for subscriber 2
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
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
    And we post to "/subscribers" with success
    """
    {
      "name":"News1","media_type":"media", "subscriber_type": "digital",
      "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
      "products": ["#products._id#"],
      "destinations":[{"name":"destination1","format": "nitf", "delivery_type":"FTP","config":{"ip":"144.122.244.55","password":"xyz"}}]
    }
    """
    When we patch "/subscribers/#subscribers._id#"
    """
    {"global_filters":{"#content_filters._id#":true}}
    """
    Then we get updated response
    """
    {"global_filters":{"#content_filters._id#":true}}
    """

  @auth
  Scenario: Generate token for subscriber
    Given "products"
      """
      [{
        "_id":"prod-1", "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }]
      """
    Given "subscribers"
    """
    [{"name": "Foo", "api_products": ["prod-1"]}]
    """

    When we post to "subscriber_token"
    """
    {"subscriber": "#subscribers._id#", "expiry_days": 7}
    """

    Then we get new resource
    """
    {"expiry": "__any_value__"}
    """
