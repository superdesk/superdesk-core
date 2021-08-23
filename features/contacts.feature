Feature: Contacts

    @auth
    @notification
    Scenario: Create a contact
        Given empty "contacts"
        When we post to "/contacts"
        """
        {
            "first_name": "Albert", "last_name": "Foo", "mobile": [{"number": "1234", "usage": "After hours",
            "public": true}], "public": true
        }
        """
        Then we get response code 201
        When we get "/contacts"
        Then we get existing resource
          """
          {
            "_items" :
              [{
              "last_name" : "Foo", "first_name" : "Albert", "mobile": [{"number": "1234", "usage": "After hours",
              "public": true}], "public": true}
              ]
          }
          """
        Then we get notifications
        """
        [{"event": "contacts:create", "extra": {"_id": ["#contacts._id#"]}}]
        """

    @auth
    Scenario: Get contacts
        Given "contacts"
        """
        [{"_id":1, "first_name": "Albert", "last_name": "Foo", "public": true},
        {"_id":2, "first_name": "Jane", "last_name": "Doe", "public": true}]
        """
        When we get "contacts"
        Then we get existing resource
          """
          {
            "_items" :
              [
                {"last_name" : "Foo", "first_name" : "Albert", "public": true},
                {"last_name" : "Doe", "first_name" : "Jane", "public": true}
              ]
          }
          """

    @auth
    Scenario: Get active contacts
        Given "contacts"
        """
        [{"_id":1, "first_name": "Albert", "last_name": "Foo","public" : true},
        {"_id":4, "is_active": false,"first_name": "Jane", "last_name": "Doe"}]
        """
        When we get "/contacts"
        Then We get list with 1 items

    @auth
    Scenario: Get all contacts
        Given "contacts"
        """
        [{"_id":1, "first_name": "Albert", "last_name": "Foo"},
        {"_id":2, "is_active": false,"first_name": "Jane", "last_name": "Doe"}]
        """
        When we get "/contacts?all=1"
        Then We get list with 2 items

    @auth
    Scenario: Get a contact
        Given "contacts"
        """
        [{"_id": 1, "first_name": "Albert", "last_name": "Foo"},
        {"_id": 4, "first_name": "Jane", "last_name": "Doe"}]
        """
        When we get "/contacts/4"
        Then we get existing resource
          """
          {
              "last_name" : "Doe", "first_name" : "Jane"
          }
          """

    @auth
    Scenario: Search for a contact
        Given "contacts"
        """
        [{"_id": 1, "first_name": "Albert", "last_name": "Foo", "public": true},
        {"_id": 2, "first_name": "Jill", "last_name": "Smith", "public": true},
        {"_id": 3, "first_name": "Bill", "last_name": "Lee", "public": true},
        {"_id": 4, "first_name": "Jane", "last_name": "Doe", "public": true}]
        """
        When we get "/contacts?q=jane"
        Then we get existing resource
          """
          {
            "_items": [{
              "last_name" : "Doe", "first_name" : "Jane", "public": true}]
          }
          """

    @auth
    @notification
    Scenario: Delete a contact
        Given "contacts"
        """
        [{"_id": "1", "first_name": "Albert", "last_name": "Foo"}]
        """
        When we delete "/contacts/1"
        Then we get response code 204
        When we get "/contacts?all=1"
        Then We get list with 0 items
        Then we get notifications
        """
        [{"event": "contacts:deleted", "extra": {"_id": ["#contacts._id#"]}}]
        """

    @auth
    @notification
    Scenario: Update a contact
        Given "contacts"
        """
        [{"_id":"1", "first_name": "Albert", "last_name": "Foo"}]
        """
        When we patch "/contacts/1"
        """
        {"first_name": "Mary", "country": {"name": "Argentina", "qcode": "arg"}, "contact_state": {"name" : "New Zealand", "qcode" : "NZ"}}
        """
        When we get "/contacts/1"
        Then we get existing resource
          """
          {
              "last_name" : "Foo", "first_name" : "Mary", "country": {"name": "Argentina", "qcode": "arg"}, "contact_state": {"name" : "New Zealand", "qcode" : "NZ"}
          }
          """
        Then we get notifications
        """
        [{"event": "contacts:update", "extra": {"_id": ["#contacts._id#"]}}]
        """
        When we patch "/contacts/1"
        """
        {"twitter": "@foo"}
        """
        Then we get updated response
        """
        {
            "last_name" : "Foo", "first_name" : "Mary", "twitter": "@foo"
        }
        """
        When we patch "/contacts/1"
        """
        {"twitter": ""}
        """
        Then we get updated response
        """
        {
            "last_name" : "Foo", "first_name" : "Mary", "twitter": ""
        }
        """
        When we patch "/contacts/1"
        """
        {"twitter": "foo"}
        """
        Then we get error 400


    @auth
    Scenario: Update a contact without permission
        Given "contacts"
        """
        [{"_id":"1", "first_name": "Albert", "last_name": "Foo"}]
        """
        When we patch "/contacts/1"
        """
        {"first_name": "Mary"}
        """
        When we switch user
        When we patch "/users/#USERS_ID#"
        """
        {"user_type": "user", "privileges": {"contacts":0}}
        """
        When we patch "/contacts/1"
        """
        {"first_name": "Jane"}
        """
        Then we get error 403

    @auth
    Scenario: Search for organisation
        Given "contacts"
        """
        [{"_id":"1", "organisation": "Foo shoes"},
        {"_id":"2", "organisation": "Foo socks"},
        {"_id":"3", "organisation": "Boo shoes"}]
        """
        When we get "/contacts/organisations?q=foo so"
        Then we get list with 1 items
        """
        {"_items": [{"organisation": "Foo socks"}]}
        """

    @auth
    Scenario: Search for organisation with no duplicates
        Given "contacts"
        """
        [{"_id":"1", "organisation": "Foo shoes"},
        {"_id":"2", "organisation": "Foo socks"},
        {"_id":"3", "organisation": "Foo shoes"}]
        """
        When we get "/contacts/organisations?q=foo"
        Then we get list with 2 items
        """
        {"_items": [{"organisation": "Foo socks"}]}
        """