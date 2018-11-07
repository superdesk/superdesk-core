Feature: Ingest using FTP feeding service

    @auth @vocabulary @provider
    Scenario: Ingest fetch stories
        Given empty "ingest"
        When we fetch from "ftp_ninjs" ingest "ninjs1.json"
        And we get "/ingest"
        Then we get existing resource
        """
        {
           "_items":[{"type": "text", "headline": "headline"}]
        }
        """

    @auth @vocabulary @provider
    Scenario: Run update_ingest command
        Given empty "ingest"
        When we run update_ingest command for "ftp_ninjs"
        And we get "/ingest"
        Then we get existing resource
        """
        {
            "_items": [
                {"type": "text", "headline": "headline 1"},
                {"type": "text", "headline": "headline 2"},
                {"type": "text", "headline": "headline 3"}
            ]
        }
        """
