Feature: item.extra storage

    @auth
    Scenario: It can store any data
        When we post to "/archive"
        """
        {"type": "text", "version": 1, "extra": {"foo": "2019-12-17T10:37:00+0000"}}
        """
        Then we get OK response

        When we post to "/archive"
        """
        {"type": "text", "version": 1, "extra": {"foo": ""}}
        """
        Then we get OK response
