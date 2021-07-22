Feature: Attachments

    @auth
    Scenario: Upload an attachment
        When we get "attachments"
        Then we get list with 0 items

        When we upload a file "bike.jpg" to "/attachments"
        """
        {
            "title": "Bike",
            "description": "bike"
        }
        """
        Then we get new resource
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

        When we patch latest
        """
        {"title": "Bike 2", "description": "bike 2"}
        """
        Then we get updated response

        When we delete latest
        Then we get error 405
