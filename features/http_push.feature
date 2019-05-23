Feature: HTTP Push publishing

    @auth
    @http_mock_adapter
    Scenario: Publish a text item
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
        [{"_id": "foo", "schema": {"body_html": {}, "slugline": {}}}]
        """
        Given "desks"
        """
        [{"name": "sports"}]
        """
        Given "vocabularies"
        """
        [{
            "_id": "rightsinfo",
            "display_name": "Copyrights",
            "type": "manageable",
            "items": [
                {
                    "is_active": true,
                    "name": "default",
                    "copyrightHolder": "copyright holder",
                    "copyrightNotice": "copyright notice",
                    "usageTerms": ""
                }
            ]
        }]
        """

        When we post to "archive"
        """
        {"profile": "foo", "type": "text", "task": {"desk": "#desks._id#"}, "byline": "foo"}
        """

        When we patch "archive/#archive._id#"
        """
        {"slugline": "slug", "body_html": "body", "headline": "Foo", "associations": {"embedded123": null}}
        """

        When we publish "#archive._id#" with "publish" type and "published" state
        Then we get OK response

        When we transmit published
        Then we pushed 1 item
        """
        [{
            "guid": "#archive.guid#",
            "profile": "foo",
            "type": "text",
            "byline": "__no_value__",
            "headline": "__no_value__",
            "body_html": "body",
            "version": "3",
            "copyrightholder": "copyright holder",
            "copyrightnotice": "copyright notice",
            "language": "en"
        }]
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

        When we rewrite "#archive._id#"
        And we publish "#REWRITE_ID#" with "publish" type and "published" state
        And we transmit published
        Then we pushed 1 item
        """
        [{"guid": "#REWRITE_ID#", "evolvedfrom": "#archive.guid#"}]
        """

        When we publish "#archive._id#" with "kill" type and "killed" state
        When we transmit published
        Then we pushed 1 item
        """
        [{"guid": "#archive.guid#", "type": "text", "pubstatus": "canceled", "version": "5"}]
        """
