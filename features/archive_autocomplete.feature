Feature: Archive autocomplete

    @auth
    Scenario: Not enabled by default
        When we get "/archive_autocomplete?field=slugline&language=en"
        Then we get error 404

    @auth
    Scenario: Get distinct sluglines for published items
        Given config update
        """
        {
            "ARCHIVE_AUTOCOMPLETE": true,
            "ARCHIVE_AUTOCOMPLETE_DAYS": 9999
        }
        """
        Given "archive"
        """
        [
            {"slugline": "PUBLISHED-A", "state": "published", "versioncreated": "2019-01-01T00:00:00+0000"},
            {"slugline": "PUBLISHED-OLD", "state": "published", "versioncreated": "1919-01-01T00:00:00+0000"},
            {"slugline": "DRAFT", "state": "draft", "versioncreated": "2019-01-01T00:00:00+0000"},
            {"slugline": "CZECH", "state": "published", "versioncreated": "2019-01-01T00:00:00+0000", "language": "cs"},
            {"slugline": "PUBLISHED-C", "state": "published", "versioncreated": "2019-01-01T00:00:00+0000", "language": "en"},
            {"slugline": "PUBLISHED-B", "state": "published", "versioncreated": "2019-01-01T00:00:00+0000", "language": "en"}
        ]
        """
        When we get "/archive_autocomplete?field=slugline&language=en"
        Then we get list with 3 items
        """
        {"_items": [
            {"value": "PUBLISHED-A"},
            {"value": "PUBLISHED-B"},
            {"value": "PUBLISHED-C"}
        ]}
        """
