
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
    {"errors": []}
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
    {"errors": []}
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
    {"errors": []}
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
    {"errors": []}
    """

  @auth
  Scenario: Validate using content type
      Given "content_types"
      """
      [{"_id": "snap", "schema": {
        "headline": {"enabled": true},
        "foo": {"required": true},
        "image": {"type": "picture"}
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
