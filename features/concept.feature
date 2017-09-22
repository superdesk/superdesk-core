Feature: Concept

    @auth
    Scenario: Create a contact in concept
        Given empty "concept"
        When we post to "/concept/contact"
        """
        {
          "concept_type": "contact",
          "contact": {"first_name": "Albert", "last_name": "Foo", "mobile": [{"number": "1234", "usage": "After hours"}]}
        }
        """
        Then we get response code 201
        When we get "/concept/contact"
        Then we get existing resource
          """
          {
            "_items" :
              [{"contact" : {
              "last_name" : "Foo", "first_name" : "Albert", "mobile": [{"number": "1234", "usage": "After hours"}]}}
              ]
          }
          """

    @auth
    Scenario: Get contacts from concept
        Given "concept"
        """
        [{"_id":1, "concept_type": "contact", "contact": {"first_name": "Albert", "last_name": "Foo"}},
        {"_id":2, "concept_type": "something", "something": {"size": 2}},
        {"_id":3, "concept_type": "something", "something": {"size": 3}},
        {"_id":4, "concept_type": "contact", "contact": {"first_name": "Jane", "last_name": "Doe"}}]
        """
        When we get "/concept/contact"
        Then we get existing resource
          """
          {
            "_items" :
              [{"contact" : {
              "last_name" : "Foo", "first_name" : "Albert"}},
              {"contact" : {
              "last_name" : "Doe", "first_name" : "Jane"}}
              ]
          }
          """

    @auth
    Scenario: Get active contacts from concept
        Given "concept"
        """
        [{"_id":1, "concept_type": "contact", "contact": {"first_name": "Albert", "last_name": "Foo"}},
        {"_id":2, "concept_type": "something", "something": {"size": 2}},
        {"_id":3, "concept_type": "something", "something": {"size": 3}},
        {"_id":4, "is_active": false, "concept_type": "contact", "contact": {"first_name": "Jane", "last_name": "Doe"}}]
        """
        When we get "/concept/contact"
        Then We get list with 1 items

    @auth
    Scenario: Get all contacts from concept
        Given "concept"
        """
        [{"_id":1, "concept_type": "contact", "contact": {"first_name": "Albert", "last_name": "Foo"}},
        {"_id":2, "concept_type": "something", "something": {"size": 2}},
        {"_id":3, "concept_type": "something", "something": {"size": 3}},
        {"_id":4, "is_active": false, "concept_type": "contact", "contact": {"first_name": "Jane", "last_name": "Doe"}}]
        """
        When we get "/concept/contact?all=1"
        Then We get list with 2 items

    @auth
    Scenario: Get a contact from concept
        Given "concept"
        """
        [{"_id":"1", "concept_type": "contact", "contact": {"first_name": "Albert", "last_name": "Foo"}},
        {"_id":"2", "concept_type": "something", "something": {"size": 2}},
        {"_id":"3", "concept_type": "something", "something": {"size": 3}},
        {"_id":"4", "concept_type": "contact", "contact": {"first_name": "Jane", "last_name": "Doe"}}]
        """
        When we get "/concept/contact/4"
        Then we get existing resource
          """
          {
            "contact" : {
              "last_name" : "Doe", "first_name" : "Jane"}
          }
          """

    @auth
    Scenario: Search for a contact
        Given "concept"
        """
        [{"_id":"1", "concept_type": "contact", "contact": {"first_name": "Albert", "last_name": "Foo"}},
        {"_id":"2", "concept_type": "something", "something": {"size": 2}},
        {"_id":"3", "concept_type": "something", "something": {"size": 3}},
        {"_id":"4", "concept_type": "contact", "contact": {"first_name": "Jane", "last_name": "Doe"}}]
        """
        When we get "/concept/contact?q=jane"
        Then we get existing resource
          """
          {
            "_items": [{
            "contact" : {
              "last_name" : "Doe", "first_name" : "Jane"}}]
          }
          """

    @auth
    Scenario: Delete a contact
        Given "concept"
        """
        [{"_id":"1", "concept_type": "contact", "contact": {"first_name": "Albert", "last_name": "Foo"}}]
        """
        When we delete "/concept/contact/1"
        Then we get response code 204
        When we get "/concept/contact?all=1"
        Then We get list with 0 items

    @auth
    Scenario: Update a contact
        Given "concept"
        """
        [{"_id":"1", "concept_type": "contact", "contact": {"first_name": "Albert", "last_name": "Foo"}}]
        """
        When we patch "/concept/contact/1"
        """
        {"contact": {"first_name": "Mary"}}
        """
        When we get "/concept/contact/1"
        Then we get existing resource
          """
          {
            "contact" : {
              "last_name" : "Foo", "first_name" : "Mary"}
          }
          """

    @auth
    Scenario: Update a contact without permission
        Given "concept"
        """
        [{"_id":"1", "concept_type": "contact", "contact": {"first_name": "Albert", "last_name": "Foo"}}]
        """
        When we patch "/concept/contact/1"
        """
        {"contact": {"first_name": "Mary"}}
        """
        When we switch user
        When we patch "/users/#USERS_ID#"
        """
        {"user_type": "user", "privileges": {"concept":0}}
        """
        When we patch "/concept/contact/1"
        """
        {"contact": {"first_name": "Jane"}}
        """
        Then we get error 403
