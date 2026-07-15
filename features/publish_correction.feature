Feature: Content Correction
    @auth
    Scenario: Sending correction succeeds when item not in publish queue
        # Setup the Product, Subscriber, Desk and Content
        When we post to "/products" with success
        """
        {"name": "prod-1", "codes": "abc,xyz", "product_type": "both"}
        """
        When we post to "/subscribers" with "sub1" and success
        """
        {
            "name": "Channel direct", "media_type": "media", "subscriber_type": "wire",
            "sequence_num_settings": {"min" : 1, "max" : 10}, "email": "test@test.com",
            "products": ["#products._id#"], "is_active": true,
            "destinations": [
                {"name": "Test","format": "nitf", "delivery_type": "email","config": {"recipients": "test@test.com"}}
            ]
        }
        """
        Given "desks"
        """
        [{"name": "Sports", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
        """
        And "archive"
        """
        [{
            "guid": "123", "headline": "test", "_current_version": 1, "state": "in_progress",
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
            "subject":[{"qcode": "17004000", "name": "Statistics"}],
            "anpa_category": [{"qcode": "a"}, {"qcode": "s"}],
            "slugline": "test",
            "body_html": "Test Document body"
        }]
        """

        # Publish the initial content item
        When we publish "#archive._id#" with "publish" type and "published" state
        Then we get OK response
        When we get "/published"
        Then we get list with 1 items
        """
        {"_items": [{"guid": "123", "headline": "test"}]}
        """
        When we get "/publish_queue"
        Then we get list with 1 items
        """
        {"_items": [{"item_id": "123", "subscriber_id": "#sub1#", "publishing_action": "published"}]}
        """

        # Empty the publish_queue collection, send a correction making sure it goes out
        Given empty "publish_queue"
        When we publish "#archive._id#" with "correct" type and "corrected" state
        """
        {"headline": "test - corrected"}
        """
        Then we get OK response
        When we get "/published"
        Then we get list with 2 items
        """
        {"_items": [
            {"guid": "123", "headline": "test"},
            {"guid": "123", "headline": "test - corrected"}
        ]}
        """
        When we get "/publish_queue"
        Then we get list with 1 items
        """
        {"_items": [{"item_id": "123", "subscriber_id": "#sub1#", "publishing_action": "corrected"}]}
        """

    @auth
    Scenario: Correcting a story should not auto-correct its associated photo unless modified

    # Setup publishing product and subscriber
    When we post to "/products" with success
    """
    {"name": "photo-test", "codes": "abc,xyz", "product_type": "both"}
    """
    When we post to "/subscribers" with "sub1" and success
    """
    {
        "name": "Photo Channel", "media_type": "media", "subscriber_type": "wire",
        "sequence_num_settings": {"min": 1, "max": 10}, "email": "photo@test.com",
        "products": ["#products._id#"], "is_active": true,
        "destinations": [
            {"name": "Test", "format": "nitf", "delivery_type": "email", "config": {"recipients": "photo@test.com"}}
        ]
    }
    """

    # Create a photo and a story with association
    Given "desks"
    """
    [{"name": "News", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
    """
    And "archive"
    """
    [
        {
        "_id": "tag:example.com,0000:newsml_PHOTO1",
        "guid": "tag:example.com,0000:newsml_PHOTO1",
        "unique_name": "photo_1",
        "type": "photo",
        "state": "in_progress",
        "headline": "Photo A",
        "task": {
            "desk": "#desks._id#",
            "stage": "#desks.incoming_stage#",
            "user": "#CONTEXT_USER_ID#"
        }
        },
        {
        "_id": "tag:example.com,0000:newsml_STORY1",
        "guid": "tag:example.com,0000:newsml_STORY1",
        "unique_name": "story_1",
        "type": "text",
        "headline": "Story A",
        "state": "in_progress",
        "associations": {
            "featuremedia": {
                "_id": "tag:example.com,0000:newsml_PHOTO1",
                "guid": "tag:example.com,0000:newsml_PHOTO1",
                "type": "picture"
            }
        },
        "task": {
            "desk": "#desks._id#",
            "stage": "#desks.incoming_stage#",
            "user": "#CONTEXT_USER_ID#"
        }
        }
    ]
    """

    # Publish both
    When we publish "tag:example.com,0000:newsml_PHOTO1" with "publish" type and "published" state
    Then we get OK response
    When we publish "tag:example.com,0000:newsml_STORY1" with "publish" type and "published" state
    Then we get OK response

    # Now correct only the story (photo should remain untouched)
    When we publish "tag:example.com,0000:newsml_STORY1" with "correct" type and "corrected" state
    """
    {"headline": "Story A - corrected"}
    """
    Then we get OK response

    # Validate correction
    When we get "/published"
    Then we get list with 3 items
    """
    {
        "_items": [
        {"guid": "tag:example.com,0000:newsml_PHOTO1", "headline": "Photo A", "state": "published"},
        {"guid": "tag:example.com,0000:newsml_STORY1", "headline": "Story A", "state": "published"},
        {"guid": "tag:example.com,0000:newsml_STORY1", "headline": "Story A - corrected", "state": "corrected"}
        ]
    }
    """

    @auth
    Scenario: Correcting a story preserves embargo timezone metadata
        # Regression test: correcting an item that has both publish_schedule and embargo
        # must not wipe schedule_settings.time_zone, otherwise the embargo shifts by the
        # UTC offset (e.g. a 10:00 local embargo can shift to 13:00 local after correction).
        When we post to "/products" with success
        """
        {"name": "prod-embargo", "codes": "abc,xyz", "product_type": "both"}
        """
        When we post to "/subscribers" with "sub1" and success
        """
        {
            "name": "Embargo Channel", "media_type": "media", "subscriber_type": "wire",
            "sequence_num_settings": {"min": 1, "max": 10}, "email": "embargo@test.com",
            "products": ["#products._id#"], "is_active": true,
            "destinations": [
                {"name": "Test", "format": "nitf", "delivery_type": "email", "config": {"recipients": "embargo@test.com"}}
            ]
        }
        """
        Given "desks"
        """
        [{"name": "News", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
        """
        And "archive"
        """
        [{
            "guid": "embargo-tz-test",
            "_id": "embargo-tz-test",
            "type": "text",
            "headline": "Embargo TZ test",
            "state": "in_progress",
            "slugline": "embargo-tz",
            "body_html": "body",
            "subject": [{"qcode": "17004000", "name": "Statistics"}],
            "anpa_category": [{"qcode": "a"}],
            "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
            "publish_schedule": "2030-04-01T10:00:00+0000",
            "embargo": "2030-04-01T10:00:00+0000",
            "schedule_settings": {
                "time_zone": "Europe/Helsinki",
                "utc_publish_schedule": "2030-04-01T07:00:00+0000",
                "utc_embargo": "2030-04-01T07:00:00+0000"
            }
        }]
        """

        When we publish "embargo-tz-test" with "publish" type and "published" state
        Then we get OK response

        When we publish "embargo-tz-test" with "correct" type and "corrected" state
        """
        {"headline": "Embargo TZ test - corrected"}
        """
        Then we get OK response

        When we get "/archive/embargo-tz-test"
        Then we get existing resource
        """
        {
            "headline": "Embargo TZ test - corrected",
            "embargo": "2030-04-01T10:00:00+0000",
            "schedule_settings": {
                "time_zone": "Europe/Helsinki",
                "utc_embargo": "2030-04-01T07:00:00+0000"
            }
        }
        """

    @auth
    Scenario: Publish new article with both published and corrected associated items

        # Step 1: Setup publishing product and subscriber
        When we post to "/products" with success
        """
        {"name": "mix-test", "codes": "abc,xyz", "product_type": "both"}
        """
        When we post to "/subscribers" with "sub-mixed" and success
        """
        {
            "name": "Mixed Channel", "media_type": "media", "subscriber_type": "wire",
            "sequence_num_settings": {"min": 1, "max": 10}, "email": "mix@test.com",
            "products": ["#products._id#"], "is_active": true,
            "destinations": [
                {
                    "name": "MixDest", "format": "nitf", "delivery_type": "email",
                    "config": {"recipients": "mix@test.com"}
                }
            ]
        }
        """

        # Step 2: Setup desks and content items
        Given "desks"
        """
        [{"name": "MixedDesk", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
        """
        And "archive"
        """
        [
            {
                "_id": "tag:example.com,2025:newsml_PUBLISHED_ARTICLE",
                "guid": "tag:example.com,2025:newsml_PUBLISHED_ARTICLE",
                "type": "text",
                "headline": "Published Article",
                "state": "in_progress",
                "task": {
                    "desk": "#desks._id#",
                    "stage": "#desks.incoming_stage#",
                    "user": "#CONTEXT_USER_ID#"
                }
            },
            {
                "_id": "tag:example.com,2025:newsml_CORRECTABLE_ARTICLE",
                "guid": "tag:example.com,2025:newsml_CORRECTABLE_ARTICLE",
                "type": "text",
                "headline": "Correctable Article",
                "state": "in_progress",
                "task": {
                    "desk": "#desks._id#",
                    "stage": "#desks.incoming_stage#",
                    "user": "#CONTEXT_USER_ID#"
                }
            }
        ]
        """

        # Step 3: Publish both articles
        When we publish "tag:example.com,2025:newsml_PUBLISHED_ARTICLE" with "publish" type and "published" state
        Then we get OK response

        When we publish "tag:example.com,2025:newsml_CORRECTABLE_ARTICLE" with "publish" type and "published" state
        Then we get OK response

        # Step 4: Send a correction to the second article
        When we publish "tag:example.com,2025:newsml_CORRECTABLE_ARTICLE" with "correct" type and "corrected" state
        """
        {"headline": "Corrected Article"}
        """
        Then we get OK response

        # Step 5: Create a new article with both published and corrected items as associations
        When we post to "/archive" with "tag:example.com,2025:newsml_MAIN_ARTICLE" and success
        """
        {
            "_id": "tag:example.com,2025:newsml_MAIN_ARTICLE",
            "guid": "tag:example.com,2025:newsml_MAIN_ARTICLE",
            "type": "text",
            "headline": "Main Article with Mixed Associations",
            "state": "in_progress",
            "task": {
                "desk": "#desks._id#",
                "stage": "#desks.incoming_stage#",
                "user": "#CONTEXT_USER_ID#"
            },
            "associations": {
                "related-published": {
                    "_id": "tag:example.com,2025:newsml_PUBLISHED_ARTICLE",
                    "guid": "tag:example.com,2025:newsml_PUBLISHED_ARTICLE",
                    "type": "text"
                },
                "related-corrected": {
                    "_id": "tag:example.com,2025:newsml_CORRECTABLE_ARTICLE",
                    "guid": "tag:example.com,2025:newsml_CORRECTABLE_ARTICLE",
                    "type": "text"
                }
            }
        }
        """

        # Step 6: Publish the new article with both associated items
        When we publish "tag:example.com,2025:newsml_MAIN_ARTICLE" with "publish" type and "published" state
        Then we get OK response

        # Step 7: Verify that all items are in published/corrected state
        When we get "/published"
        Then we get list with 4 items
        """
        {
            "_items": [
                {
                    "guid": "tag:example.com,2025:newsml_PUBLISHED_ARTICLE",
                    "headline": "Published Article",
                    "state": "published"
                },
                {
                    "guid": "tag:example.com,2025:newsml_CORRECTABLE_ARTICLE",
                    "headline": "Correctable Article",
                    "state": "published"
                },
                {
                    "guid": "tag:example.com,2025:newsml_CORRECTABLE_ARTICLE",
                    "headline": "Corrected Article",
                    "state": "corrected"
                },
                {
                    "guid": "tag:example.com,2025:newsml_MAIN_ARTICLE",
                    "headline": "Main Article with Mixed Associations",
                    "state": "published"
                }
            ]
        }
        """

    @auth
    Scenario: API mismatch archive correction vs published state is handled gracefully
        Given config update
        """
        {"CORRECTIONS_WORKFLOW": true}
        """
        And "validators"
        """
        [
            {"_id": "publish_text", "act": "publish", "type": "text", "schema": {}},
            {"_id": "correct_text", "act": "correct", "type": "text", "schema": {}}
        ]
        """
        And "desks"
        """
        [{"name": "Sports", "members": [{"user": "#CONTEXT_USER_ID#"}]}]
        """
        And "archive"
        """
        [{
            "_id": "mismatch-123",
            "guid": "mismatch-123",
            "type": "text",
            "headline": "Mismatch candidate",
            "state": "fetched",
            "_current_version": 1,
            "task": {
                "desk": "#desks._id#",
                "stage": "#desks.incoming_stage#",
                "user": "#CONTEXT_USER_ID#"
            },
            "subject": [{"qcode": "17004000", "name": "Statistics"}],
            "body_html": "Body"
        }]
        """

        When we publish "mismatch-123" with "publish" type and "published" state
        Then we get OK response

        When we publish "mismatch-123" with "correction" type and "correction" state
        Then we get OK response

        When we get "/archive/mismatch-123"
        Then we get existing resource
        """
        {"state": "correction"}
        """

        When we get "/published/mismatch-123"
        Then we get existing resource
        """
        {"state": "being_corrected"}
        """

        When we patch "/published/mismatch-123"
        """
        {"state": "published"}
        """
        Then we get updated response

        When we publish "mismatch-123" with "correct" type and "corrected" state
        Then we get response code 200

        When we get "/archive/mismatch-123"
        Then we get existing resource
        """
        {"state": "corrected"}
        """

        When we get "/published"
        Then we get list with 2 items
        """
        {
            "_items": [
                {"guid": "mismatch-123", "state": "published"},
                {"guid": "mismatch-123", "state": "corrected"}
            ]
        }
        """

