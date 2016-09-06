Feature: HTTP Push publishing

    @auth
    @http_mock_adapter
    Scenario: Publish a text item without takes package
        Given config update
        """
        {"NO_TAKES": true}
        """
        Given "products"
        """
        [{"name": "all"}]
        """
        Given "subscribers"
        """
        [{
            "name": "http",
            "media_type": "media",
            "subscriber_type": "digital",
            "products": ["#products._id#"],
            "destinations": [
                {
                    "name": "destination1",
                    "format": "ninjs",
                    "delivery_type": "http_push",
                    "config": {
                        "resource_url": "mock://publish",
                        "assets_url": "mock://assets",
                        "packaged": "true"
                    }
                }
            ]
        }]
        """
        Given "content_types"
        """
        [{"_id": "foo", "schema": {}}]
        """
        Given "desks"
        """
        [{"name": "sports"}]
        """

        When we post to "archive"
        """
        {"profile": "foo", "type": "text", "task": {"desk": "#desks._id#"}}
        """

        When we patch "archive/#archive._id#"
        """
        {"slugline": "slug", "body_html": "body"}
        """

        When we publish "#archive._id#" with "publish" type and "published" state
        Then we get OK response

        When we transmit published
        Then we pushed 1 item
        """
        [{"guid": "#archive.guid#", "profile": "foo", "type": "text", "body_html": "body", "version": "3"}]
        """

        When we publish "#archive._id#" with "correct" type and "corrected" state
        """
        {"body_html": "corrected"}
        """

        When we transmit published
        Then we pushed 1 item
        """
        [{"guid": "#archive.guid#", "type": "text", "version": "4", "body_html": "corrected"}]
        """

        When we publish "#archive._id#" with "kill" type and "killed" state
        When we transmit published
        Then we pushed 1 item
        """
        [{"guid": "#archive.guid#", "type": "text", "pubstatus": "canceled", "version": "5"}]
        """
