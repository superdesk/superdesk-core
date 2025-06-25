Feature: Correct and republish story with photo

  @auth
  Scenario: Correct and republish a story with photo, then update again
    # Setup a product and subscriber for publishing
    When we post to "/products" with success
    """
    {"name": "prod-1", "codes": "abc,xyz", "product_type": "both"}
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

    # Create desks and content
    Given "desks"
    """
    [{"name": "News", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
    """
    And "archive"
    """
    [
      {
        "_id": "photo_1",
        "guid": "photo_1",
        "unique_name": "photo_1",
        "type": "photo",
        "state": "in_progress",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "headline": "Original Photo"
      },
      {
        "_id": "story_1",
        "guid": "story_1",
        "unique_name": "story_1",
        "type": "text",
        "state": "in_progress",
        "headline": "Original Story",
        "associations": {
            "featuremedia": {
                "_id": "photo_1",
                "guid": "photo_1",
                "type": "picture"
            }
        },
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}
      }
    ]
    """

    # Publish photo and story
    When we publish "photo_1" with "publish" type and "published" state
    Then we get OK response
    When we publish "story_1" with "publish" type and "published" state
    Then we get OK response

    # Correct story
    When we publish "photo_1" with "correct" type and "corrected" state
    """
    {"headline": "Corrected Photo"}
    """
    Then we get OK response
    When we publish "story_1" with "correct" type and "corrected" state
    """
    {"headline": "Corrected Story"}
    """
    Then we get OK response

    # Confirm both are in corrected state
    When we get "/published"
    Then we get list with 4 items
    """
    {
      "_items": [
        {"guid": "photo_1", "headline": "Original Photo"},
        {"guid": "story_1", "headline": "Original Story"},
        {"guid": "photo_1", "headline": "Corrected Photo"},
        {"guid": "story_1", "headline": "Corrected Story"}
      ]
    }
    """

    # Update the story after correction
    When we patch "/published/story_1"
    """
    {"headline": "Updated Corrected Story"}
    """

    # Republish again
    When we publish "story_1" with "publish" type and "published" state
    Then we get OK response

    # Final check in /published
    When we get "/published"
    Then we get list with 5 items
    """
    {
      "_items": [
        {"guid": "story_1", "headline": "Updated Corrected Story"}
      ]
    }
    """
