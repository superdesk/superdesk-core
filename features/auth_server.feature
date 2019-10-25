Feature: Authorization Server

    Scenario: Valid client authenticate with success
        Given authorized clients
            """
            [{"name": "test_client", "client_id": "0102030405060708090a0b0c", "password": "secret_pwd_123", "scope": ["ARCHIVE_READ"]}]
            """

        When we do OAuth2 client authentication with id "0102030405060708090a0b0c" and password "secret_pwd_123"

        Then we get a valid access token


	Scenario: Invalid client can't authenticate
        Given authorized clients
            """
            [{"name": "test_client_2", "client_id": "0102030405060708090a0b0c", "password": "secret_pwd_123", "scope": ["ARCHIVE_READ"]}]
            """

        When we do OAuth2 client authentication with id "0102030405060708090a0b0c" and password "bad_secret_pwd"

        Then we don't get an access token
