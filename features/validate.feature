Feature: Validate

  @auth
  Scenario: Validate type
    Given the "validators"
      """
      [{"_id": "publish", "act": "publish", "type": "text", "schema":{"headline": {"type": "string"}}}]
      """
    When we post to "/validate"
      """
      {"act": "publish", "type": "text", "validate": {"headline": true}}
      """
    Then we get existing resource
    """
    {"errors": ["HEADLINE must be of string type"]}
    """

  @auth
  Scenario: Validate pass
    Given the "validators"
      """
      [{"_id": "publish", "act": "publish", "type": "text", "schema":{"headline": {"type": "string"}}}]
      """
    When we post to "/validate"
      """
      {"act": "publish", "type": "text", "validate": {"headline": "budget cigs and beer up"}}
      """
    Then we get existing resource
    """
    {"errors": "__empty__"}
    """

  @auth
  Scenario: Validate required field
    Given the "validators"
      """
      [{"_id": "publish", "act": "publish", "type": "text", "schema":{"headline": {"type": "string", "required": true}}}]
      """
    When we post to "/validate"
      """
      {"act": "publish", "type": "text", "validate": {"not headline": "budget cigs and beer up"}}
      """
    Then we get existing resource
    """
    {"errors": ["HEADLINE is a required field"]}
    """
  @auth
  Scenario: Validate field length short
    Given the "validators"
      """
      [{"_id": "publish",
        "act": "publish",
        "type": "text",
        "schema":{
          "headline": {
            "type": "string",
            "minlength": 2,
            "maxlength": 55}}}]
      """
    When we post to "/validate"
      """
      {"act": "publish", "type": "text", "validate": {"headline": "1"}}
      """
    Then we get existing resource
    """
    {"errors": ["HEADLINE is too short"]}
    """

  @auth
  Scenario: Validate field minimum length fails
    Given the "validators"
      """
      [{"_id": "publish",
        "act": "publish",
        "type": "text",
        "schema":{
          "headline": {
            "type": "string",
            "minlength": 2,
            "required": true,
            "maxlength": 55}}}]
      """
    When we post to "/validate"
      """
      {"act": "publish", "type": "text", "validate": {"headline": "<p></p>"}}
      """
    Then we get existing resource
    """
    {"errors": ["HEADLINE is too short"]}
    """

  @auth
  Scenario: Validate field maximum length passes
    Given the "validators"
      """
      [{"_id": "publish",
        "act": "publish",
        "type": "text",
        "schema":{
          "headline": {
            "type": "string",
            "maxlength": 9}}}]
      """
    When we post to "/validate"
      """
      {"act": "publish", "type": "text", "validate": {"headline": "<p>123456789</p>"}}
      """
    Then we get existing resource
    """
    {"errors": "__empty__"}
    """

  @auth
  Scenario: Validate field length long
    Given the "validators"
      """
      [{"_id": "publish", "act": "publish", "type": "text", "schema":{"headline": {"type": "string", "minlength": 2, "maxlength": 3}}}]
      """
    When we post to "/validate"
      """
      {"act": "publish", "type": "text", "validate": {"headline": "1234"}}
      """
    Then we get existing resource
    """
    {"errors": ["HEADLINE is too long"]}
    """

  @auth
  Scenario: Validate allowed values
    Given the "validators"
      """
      [{"_id": "publish", "act": "publish", "type": "text", "schema":{"type": {"type": "string", "allowed": ["X","T"]}}}]
      """
    When we post to "/validate"
      """
      {"act": "publish", "type": "text", "validate": {"type": "B"}}
      """
    Then we get existing resource
    """
    {"errors": ["TYPE unallowed value B"]}
    """
  @auth
  Scenario: Validate allow unknown fields
    Given the "validators"
      """
      [{"_id": "publish", "act": "publish", "type": "text", "schema":{}}]
      """
    When we post to "/validate"
      """
      {"act": "publish", "type": "text", "validate": {"unknown": "B"}}
      """
    Then we get existing resource
    """
    {"errors": "__empty__"}
    """
  @auth
  Scenario: Missing validator
    Given the "validators"
      """
      [{"_id": "publish", "act": "publish", "type": "text", "schema":{}}]
      """
    When we post to "/validate"
      """
      {"act": "missing", "type": "text", "validate": {"unknown": "B"}}
      """
    Then we get existing resource
    """
    {"errors": "__empty__"}
    """

  @auth
  Scenario: Validate using content type
      Given "content_types"
      """
      [{"_id": "snap", "schema": {
        "headline": {"enabled": true},
        "foo": {"required": true},
        "image": {"type": "media"},
        "genre": {"genre": {"value": "foo"}, "type": "string"}
      }}]
      """
      When we post to "/validate"
      """
      {"act": "publish", "type": "text", "validate": {"slugline": "x", "profile": "snap"}}
      """
      Then we get existing resource
      """
      {"errors": ["FOO is a required field"]}
      """

  @auth
  Scenario: Validate custom field
    Given "vocabularies"
    """
    [{"_id": "custom", "field_type": "text", "display_name": "Test"}]
    """
    And "content_types"
    """
    [{"_id": "foo", "schema": {
      "custom": {"required": true}
    }}]
    """

    When we post to "/validate"
    """
    {"act": "publish", "type": "text", "validate": {"profile": "foo"}}
    """
    Then we get existing resource
    """
    {"errors": ["Test is a required field"]}
    """

    When we post to "/validate"
    """
    {"act": "publish", "type": "text", "validate": {"profile": "foo", "extra": {"custom": "foo"}}}
    """
    Then we get existing resource
    """
    {"errors": "__empty__"}
    """

    When we post to "/validate"
    """
    {"act": "publish", "type": "text", "validate": {"profile": "foo", "extra": {"custom": "<p></p>"}}}
    """
    Then we get existing resource
    """
    {"errors": ["Test is a required field"]}
    """

  @auth
  Scenario: Validate using custom package schema
    Given config update
    """
    {"SCHEMA": {"composite": {"headline": {"type": "text", "required": true}}}}
    """

    When we post to "/validate"
    """
    {"act": "publish", "type": "composite", "validate": {"slugline": "foo"}}
    """

    Then we get existing resource
    """
    {"errors": ["HEADLINE is a required field"]}
    """

  @auth
  Scenario: Validate multiple required custom fields
    Given "vocabularies"
    """
    [
        {"_id": "text1", "field_type": "text", "display_name": "Text 1"},
        {"_id": "media1", "field_type": "media", "display_name": "Media 1"},
        {"_id": "embed1", "field_type": "embed", "display_name": "Embed 1"},
        {"_id": "date1", "field_type": "date", "display_name": "Date 1"},
        {"_id": "vocabulary1", "field_type": null, "display_name": "Vocabulary 1"}
    ]
    """
    And "content_types"
    """
    [{"_id": "foo", "schema": {
      "text1": {"required": true},
      "media1": {"required": true},
      "embed1": {"required": true},
      "date1": {"required": true},
      "subject": {
        "mandatory_in_list": {"scheme": {"vocabulary1": {"required": true}}},
        "type": "list"
      }
    }}]
    """

    When we post to "/validate"
    """
    {"act": "publish", "type": "text", "validate": {"profile": "foo", "subject": []}}
    """
    Then we get existing resource
    """
    {"errors": ["Text 1 is a required field", "MEDIA 1 is a required field",
        "Embed 1 is a required field", "Date 1 is a required field", "VOCABULARY 1 is a required field"
    ]}
    """

    When we post to "/validate"
    """
    {
        "act": "publish", "type": "text",
        "validate": {
            "profile": "foo",
            "extra": {
                "text1": "foo",
                "embed1": {"foo": "bar"},
                "date1": "2018-01-22T00:00:00+0000"
            },
            "associations": {
                "media1": {
                    "foo": "bar",
                    "headline": "headline",
                    "alt_text": "alt_text",
                    "description_text": "description_text"
                    }
            }
        }
    }
    """
    Then we get existing resource
    """
    {"errors": "__empty__"}
    """

  @auth
  Scenario: Validate subject field with missing scheme
  Given "content_types"
    """
    [{"_id": "test", "schema": {
      "subject": {
        "mandatory_in_list": {"scheme": {"01": {"required": "true"}, "destination": null}},
        "type": "list",
        "nullable": true,
        "required": false,
        "schema": {
          "type": "dict",
          "schema": {
            "scheme": {
              "allowed": ["01"],
              "nullable": true,
              "required": true,
              "type": "string"
            }
          }
        }
      }
    }}]
    """

    When we post to "/validate"
    """
    {
      "act": "publish", "type": "text",
      "validate": {
        "profile": "test",
        "subject": [{"name": "foo", "qcode": "foo"}, {"name": "01", "qcode": "01", "scheme": "01"}]
      }
    }
    """
    Then we get existing resource
    """
    {"errors": "__empty__"}
    """

  @auth
  Scenario: Validate subject with subject scheme not in allowed
  Given "content_types"
    """
    [{"_id": "test", "schema": {
      "subject": {
        "mandatory_in_list": {"scheme": {"01": {"required": "true"}, "destination": null}},
        "type": "list",
        "nullable": false,
        "required": true,
        "type": "list",
        "schema": {
          "type": "dict",
          "schema": {
            "scheme": {
              "allowed": ["01"],
              "nullable": true,
              "required": true,
              "type": "string"
            }
          }
        }
      }
    }}]
    """

    When we post to "/validate"
    """
    {
      "act": "publish", "type": "text",
      "validate": {
        "profile": "test",
        "subject": [
          {"name": "foo", "qcode": "foo", "scheme": null},
          {"name": "01", "qcode": "01", "scheme": "01"},
          {"name": "bar", "qcode": "bar", "scheme": "bar"}
        ]
      }
    }
    """
    Then we get existing resource
    """
    {"errors": "__empty__"}
    """

    @auth
    Scenario: Validate subject using custom vocabulary for it
    Given "content_types"
    """
    [{"_id": "test", "schema": {
      "subject": {
        "type": "list",
        "nullable": false,
        "required": true,
        "type": "list"
      }
    }}]
    """
    And "vocabularies"
    """
    [
      {"_id": "custom_subject_field", "schema_field": "subject"},
      {"_id": "other_field"}
    ]
    """

    When we post to "/validate"
    """
    {
      "act": "publish", "type": "text",
      "validate": {
        "profile": "test",
        "subject": [
          {"name": "foo", "qcode": "foo", "scheme": "custom_subject_field"}
        ]
      }
    }
    """

    Then we get existing resource
    """
    {"errors": "__empty__"}
    """

    When we post to "/validate"
    """
    {
      "act": "publish", "type": "text",
      "validate": {
        "profile": "test",
        "subject": [
          {"name": "foo", "qcode": "foo", "scheme": "other field"}
        ]
      }
    }
    """

    Then we get existing resource
    """
    {"errors": ["SUBJECT is a required field"]}
    """

  @auth
    Scenario: Validate picture using content profile
    Given "content_types"
    """
    [{"_id": "test", "item_type": "picture", "schema": {
      "headline": {
        "type": "string",
        "nullable": true,
        "required": true
      }
    }}]
    """

    When we post to "/validate"
    """
    {
      "act": "publish",
      "type": "picture",
      "validate": {
        "type": "picture",
        "slugline": "foo"
      }
    }
    """

    Then we get existing resource
    """
    {"errors": ["HEADLINE is a required field"]}
    """

    @auth
    Scenario: Custom subject vocabulary should display the display name if present
    Given "content_types"
    """
    [{"_id": "test", "schema": {
      "subject": {
        "type": "list",
        "nullable": false,
        "required": true,
        "type": "list"
      }
    }}]
    """
    And "vocabularies"
    """
    [
      {"_id": "custom_subject_field", "schema_field": "subject", "display_name": "Subject custom field"},
      {"_id": "other_field"}
    ]
    """

    When we post to "/validate"
    """
    {
      "act": "publish", "type": "text",
      "validate": {
        "profile": "test",
        "subject": [
          {"name": "foo", "qcode": "foo", "scheme": "custom_subject_field"}
        ]
      }
    }
    """

    Then we get existing resource
    """
    {"errors": "__empty__"}
    """

    When we post to "/validate"
    """
    {
      "act": "publish", "type": "text",
      "validate": {
        "profile": "test",
        "subject": [
          {"name": "foo", "qcode": "foo", "scheme": "other field"}
        ]
      }
    }
    """

    Then we get existing resource
    """
    {"errors": ["SUBJECT CUSTOM FIELD is a required field"]}
    """
