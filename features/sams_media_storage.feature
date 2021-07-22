@sams
Feature: SAMS Integration
    Background: Setup Set
        Given config
        """
            {"INSTALLED_APPS": ["superdesk.sams"]}
        """
        When we post to "/sams/sets"
        """
        {
            "name": "Default",
            "destination_name": "Default",
            "state": "usable"
        }
        """

    @auth
    Scenario: Upload attachment to SAMS
        Given config update
        """
        {
            "MEDIA_STORAGE_PROVIDER": "superdesk.sams.media_storage.SAMSMediaStorage"
        }
        """
        When we upload a file "bike.jpg" to "/attachments"
        """
        {
            "title": "Bike",
            "description": "bike"
        }
        """
        When we get "/attachments/#attachments._id#"
        Then we get existing resource
        """
        {
            "filename": "bike.jpg",
            "mimetype": "image/jpeg",
            "media": {"length": 469900},
            "user": "#CONTEXT_USER_ID#",
            "title": "Bike",
            "description": "bike"
        }
        """
        When we get "/sams/assets/#attachments.media._id#"
        Then we get existing resource
        """
        {
            "_id": "#attachments.media._id#",
            "name": "Bike",
            "description": "bike",
            "filename": "bike.jpg",
            "state": "public",
            "mimetype": "image/jpeg",
            "length": 469900
        }
        """

    @auth
    Scenario: Upload attachment after enabling SAMS
        When we upload a file "bike.jpg" to "/attachments"
        """
        {
            "title": "Bike",
            "description": "bike"
        }
        """
        Then we store response in "asset_1"
        Given config update
        """
        {"MEDIA_STORAGE_PROVIDER": "superdesk.sams.media_storage.SAMSMediaStorage"}
        """
        When we upload a file "test_dict.txt" to "/attachments"
        """
        {
            "title": "Test Dict",
            "description": "test dictionary"
        }
        """
        Then we store response in "asset_2"
        When we get "/attachments/#asset_1._id#"
        Then we get OK response
        When we get "/sams/assets/#asset_1.media._id#"
        Then we get error 404
        When we get "/attachments/#asset_2._id#"
        Then we get OK response
        When we get "/sams/assets/#asset_2.media._id#"
