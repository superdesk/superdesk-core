Feature: Associated photo should not be corrected unless explicitly modified

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
