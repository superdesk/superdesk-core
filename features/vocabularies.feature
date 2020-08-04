Feature: Vocabularies

  @auth
  Scenario: List category vocabulary
    Given the "vocabularies"
      """
      [{"_id": "categories", "items": [{"name": "National", "value": "A", "is_active": true}, {"name": "Domestic Sports", "value": "T", "is_active": false}]}]
      """
    When we get "/vocabularies/categories"
    Then we get existing resource
      """
      {"_id": "categories", "items": [{"name": "National", "value": "A"}]}
      """

  @auth
  Scenario: Add vocabulary with invalid identifer
    Given empty "vocabularies"
    When we post to "vocabularies"
    """
    {"_id": "foo$", "type": "manageable", "display_name": "Foo", "items": []}
    """
    Then we get response code 400

  @auth
  Scenario: List default preferred categories vocabulary
    Given the "vocabularies"
      """
      [{
          "_id": "default_categories",
          "items": [
              {"is_active": true, "qcode": "a"},
              {"is_active": false, "qcode": "b"},
              {"is_active": true, "qcode": "c"}
          ]
        }
      ]
      """
    When we get "/vocabularies/default_categories"
    Then we get existing resource
      """
      {"_id": "default_categories", "items": [{"qcode": "a"}, {"qcode": "c"}]}
      """

  @auth
  Scenario: List newsvalue vocabulary
    Given the "vocabularies"
      """
      [{"_id": "newsvalue", "items":[{"name":"1","value":"1", "is_active": true},{"name":"2","value":"2","is_active": true},{"name":"3","value":"3", "is_active": true},{"name":"4","value":"4", "is_active": false}]}]
      """
    When we get "/vocabularies/newsvalue"
    Then we get existing resource
      """
      {"_id": "newsvalue", "items":[{"name":"1","value":"1"},{"name":"2","value":"2"},{"name":"3","value":"3"}]}
      """

  @auth
  Scenario: List vocabularies
    Given the "vocabularies"
      """
      [
        {"_id": "categories", "items": [{"name": "National", "value": "A", "is_active": true}, {"name": "Domestic Sports", "value": "T", "is_active": false}]},
        {"_id": "newsvalue", "items":[{"name":"1","value":"1", "is_active": true},{"name":"2","value":"2","is_active": true},{"name":"3","value":"3", "is_active": true},{"name":"4","value":"4", "is_active": false}]}
      ]
      """
    When we get "/vocabularies"
    Then we get existing resource
      """
      {
        "_items" :
          [
            {"_id": "categories", "items": [{"name": "National", "value": "A"}]},
            {"_id": "newsvalue", "items":[{"name":"1","value":"1"},{"name":"2","value":"2"},{"name":"3","value":"3"}]}
          ]
      }
      """

  @auth
  @vocabulary
  Scenario: Fetch all when type is not specified and fetch based on type when specified
    When we get "/vocabularies"
    Then we get existing resource
    """
    {"_items" :[{"_id": "locators"}, {"_id": "categories"}]}
    """
    When we get "/vocabularies?where={"type":"manageable"}"
    Then we get existing resource
    """
    {"_items": [{"_id": "crop_sizes", "display_name": "Image Crop Sizes", "type": "manageable",
     "items": [{"is_active": true, "name": "4-3", "ratio": "4:3"},
               {"is_active": true, "name": "16-9", "ratio": "16:9"}]
     }]}
    """
    And there is no "locators" in response

  @auth @notification @vocabulary
  Scenario: User receives notification when a vocabulary is updated
    When we get "/vocabularies/categories"
    Then we get response code 200
    When we patch "/vocabularies/categories"
    """
    {"items": [{"name": "National", "qcode": "A", "is_active": true}, {"name": "Domestic Sports", "qcode": "T", "is_active": true}]}
    """
    Then we get updated response
    And we get notifications
    """
    [{"event": "vocabularies:updated", "extra": {"vocabulary": "Categories", "user": "#CONTEXT_USER_ID#"}}]
    """

  @auth @vocabulary
  Scenario: Vocabulary update fails if unique field is defined and non-unique value given
    When we get "/vocabularies/categories"
    Then we get response code 200
    When we patch "/vocabularies/categories"
    """
    {"items": [{"name": "National", "qcode": "A", "is_active": true}, {"name": "Domestic Sports", "qcode": "a", "is_active": true}]}
    """
    Then we get error 400
    """
    {"_status": "ERR",
    "_issues": {"validator exception": "400: Value a for field qcode is not unique"}}
    """

  @auth @vocabulary
  Scenario: Vocabulary update fails if unique field is defined and no value given
    When we get "/vocabularies/categories"
    Then we get response code 200
    When we patch "/vocabularies/categories"
    """
    {"items": [{"name": "National", "value": "A", "is_active": true}]}
    """
    Then we get error 400
    """
    {"_status": "ERR",
    "_issues": {"validator exception": "400: qcode cannot be empty"}}
    """

  @auth @vocabulary
  Scenario: Vocabulary update succeeds if unique field is defined
    When we get "/vocabularies/categories"
    Then we get response code 200
    When we patch "/vocabularies/categories"
    """
    {"items": [
      {"name": "National", "qcode": "A", "is_active": true},
      {"name": "Domestic Sports", "qcode": "B", "is_active": true}
     ]}
    """
    Then we get updated response

  @auth @vocabulary
  Scenario: Vocabulary update succeeds if no unique field is defined with non-unique value
    When we get "/vocabularies/genre"
    Then we get response code 200
    When we patch "/vocabularies/genre"
    """
    {"items": [
      {"name": "Article", "qcode": "A", "is_active": true},
      {"name": "Sidebar", "qcode": "A", "is_active": true},
      {"name": "Article", "qcode": "A", "is_active": true}
     ]}
    """
    Then we get updated response

  @auth
  Scenario: Cast crop image width/height to int
    Given "vocabularies"
    """
    [{"_id": "crop_sizes", "items": [
      {
        "is_active" : true,
        "width" : "300",
        "name" : "foo",
        "height" : "200"
      }
    ]}]
    """
    When we get "/vocabularies"
    Then we get list with 1 items
    """
    {"_items": [{"items": [{"width": 300, "height": 200}]}]}
    """

    When we get "/vocabularies/crop_sizes"
    Then we get existing resource
    """
    {"items": [{"width": 300, "height": 200}]}
    """

  @auth @notification
  Scenario: Create new vocabulary
    When we post to "vocabularies"
    """
    {"_id": "foo", "type": "manageable", "display_name": "Foo", "items": []}
    """
    Then we get new resource
    """
    {"_id": "foo", "type": "manageable", "display_name": "Foo", "items": []}
    """
    And we get notifications
    """
    [{"event": "vocabularies:created", "extra": {"vocabulary_id": "foo", "vocabulary": "Foo", "user": "#CONTEXT_USER_ID#"}}]
    """


  @auth
  Scenario: Create new custom field with system field id
    When we post to "vocabularies"
    """
    {"_id": "headline", "field_type": "text", "type": "manageable", "display_name": "Foo", "items": []}
    """
    Then we get error 400
    """
    {"_issues": {"_id": {"conflict": 1}}}
    """

  @auth
  Scenario: Create and remove vocabularies
    Given the "vocabularies"
	"""
	[{"_id": "categories", "items": [{"name": "National", "value": "A", "is_active": true}]},
	 {"_id": "text1", "type": "manageable", "field_type": "text", "items": []}]
	"""
	When we delete "/vocabularies/categories"
    Then we get error 400
    """
    {"_message": "Default vocabularies cannot be deleted", "_status": "ERR"}
    """
	When we delete "/vocabularies/text1"
    Then we get response code 204
    When we get "/vocabularies/text1"
    Then we get error 404

  @auth
  Scenario: Create vocabularies with missing name and qcode
    When we post to "vocabularies"
    """
    {
    	"_id": "foo", "type": "manageable", "display_name": "Foo", "items": [{"name": "name"}],
    	"schema": {"name": {"required": true}, "qcode": {"required": true}}
    }
    """
    Then we get error 400
    """
    {"_message": "Required qcode in item 0", "_status": "ERR"}
    """
    When we post to "vocabularies"
    """
    {
    	"_id": "foo", "type": "manageable", "display_name": "Foo", "items": [{"qcode": "qcode"}],
    	"schema": {"name": {"required": true}, "qcode": {"required": true}}
    }
    """
    Then we get error 400
    """
    {"_message": "Required name in item 0", "_status": "ERR"}
    """
    When we post to "vocabularies"
    """
    {"_id": "foo", "type": "manageable", "display_name": "Foo", "items": [{"foo": "bar"}]}
    """
    Then we get response code 201
    When we post to "vocabularies"
    """
    {
    	"_id": "bar", "type": "manageable", "display_name": "Bar",
    	"schema": {"name": {"required": true}, "qcode": {"required": true}}, "items": []
    }
    """
    Then we get response code 201
    When we patch "/vocabularies/bar"
    """
    {"items": [{"name": "Article"}]}
    """
    Then we get error 400
    """
    {"_issues": {"validator exception": "400: Required qcode in item 0"}, "_status": "ERR"}
    """

  @auth
  Scenario: Validate linked vocabularies
    When we post to "vocabularies"
    """
    [{
        "_id": "foo",
        "type": "manageable",
        "display_name": "Foo",
        "items": [],
        "schema": {
            "name": {"required": true},
            "qcode": {"required": true}
        }
    }, {
        "_id": "bar",
        "type": "manageable",
        "display_name": "Bar",
        "items": [],
        "schema": {
            "name": {"required": true},
            "qcode": {"required": true},
            "foo": {
                "type": "string",
                "required": false,
                "link_vocab": "foo",
                "link_field": "qcode"
            }
        }
    }]
    """
    Then we get OK response
    When we patch "/vocabularies/bar"
    """
    {
        "items": [{
            "qcode": "b1",
            "name": "B1",
            "foo": "f1"
        }]
    }
    """
    Then we get error 400
    """
    {"_issues": {"validator exception": "400: foo \"qcode=f1\" not found"}, "_status": "ERR"}
    """
    When we patch "/vocabularies/foo"
    """
    {
        "items": [{
            "qcode": "f1",
            "name": "F1"
        }]
    }
    """
    Then we get OK response
    When we patch "/vocabularies/bar"
    """
    {
        "items": [{
            "qcode": "b1",
            "name": "B1",
            "foo": "f1"
        }]
    }
    """
    Then we get OK response

  @auth @notification
  Scenario: Create new vocabulary with a label
    When we post to "vocabularies"
    """
    {"_id": "foo", "type": "manageable", "display_name": "Foo", "items": [], "tags": [{"text": "Other"}]}
    """
    Then we get new resource
    """
    {"_id": "foo", "type": "manageable", "display_name": "Foo", "items": [], "tags": [{"text": "Other"}]}
    """
    And we get notifications
    """
    [{"event": "vocabularies:created", "extra": {"vocabulary_id": "foo", "vocabulary": "Foo", "user": "#CONTEXT_USER_ID#"}}]
    """
