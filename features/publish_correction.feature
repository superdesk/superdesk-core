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
