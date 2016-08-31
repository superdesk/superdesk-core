Feature: Publish embedded items feature

    @auth
    Scenario: Publish embedded picture together with text item
        Given "vocabularies"
        """
        [{"_id": "crop_sizes", "items": [{"is_active": true, "name": "3:2", "width": 3, "height": 2}]}]
        """
        Given "validators"
        """
        [
            {
                "_id": "publish_text",
                "act": "publish",
                "type": "text",
                "schema": {
                    "headline": {"type": "string",
                        "required": true,
                        "nullable": false,
                        "empty": false,
                        "maxlength": 42
                    }
                }
            },
            {
                "_id": "publish_embedded_picture",
                "act": "publish",
                "type": "picture",
                "embedded": true,
                "schema": {
                    "type": {
                        "type": "string",
                        "required": "true",
                        "allowed": ["picture"]
                    },
                    "pubstatus": {
                        "type": "string",
                        "required": true,
                        "allowed": ["usable"]
                    },
                    "slugline": {
                        "type": "string",
                        "required": true,
                        "nullable": false,
                        "empty": false,
                        "maxlength": 24
                    }
                }
            }
        ]
        """
        Given "desks"
        """
        [{"name": "sports"}]
        """

        When we post to "archive"
        """
        {"type": "text", "task": {"desk": "#desks._id#"}, "guid": "foo"}
        """
        Then we get OK response

        When we upload a file "bike.jpg" to "archive"
        Then we get OK response

        When we patch "archive/foo"
        """
        {"headline": "foo", "slugline": "bar", "state": "in_progress", "associations": {"embedded1": {"_id": "#archive._id#", "type": "picture", "headline": "test", "state": "draft"}}}
        """
        Then we get OK response

        When we publish "foo" with "publish" type and "published" state
        Then we get error 400
        """
        {"_issues": {"validator exception": "['Associated item  test: SLUGLINE is a required field']"}}
        """

        When we patch "archive/#archive._id#"
        """
        {"slugline": "bike"}
        """
        Then we get OK response

        When we publish "foo" with "publish" type and "published" state
        """
        {"headline": "foo", "associations": {"embedded1": {"_id": "#archive._id#", "type": "picture", "headline": "test", "state": "draft"}}}
        """
        Then we get OK response
