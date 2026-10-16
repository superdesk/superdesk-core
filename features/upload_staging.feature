Feature: Upload staging

    @auth
    @vocabulary
    Scenario: Stage a picture and create an archive item from it
        When we upload a file "bike.jpg" to "upload_staging"
        Then we get new resource
        """
        {"filename": "bike.jpg", "mimetype": "image/jpeg", "meta": {}, "status": "ready", "renditions": {"viewImage": {}}}
        """
        When we post to "/archive"
        """
        {"staged_id": "#upload_staging._id#", "headline": "bike"}
        """
        Then we get response code 201
        And we get existing resource
        """
        {"type": "picture", "headline": "bike", "mimetype": "image/jpeg", "renditions": {"original": {}, "viewImage": {}}}
        """
        When we get "/upload_staging/#upload_staging._id#"
        Then we get error 404

    @auth
    @vocabulary
    Scenario: Metadata embedded in the picture is returned and used as defaults
        When we upload a file "cp.jpg" to "upload_staging"
        Then we get new resource
        """
        {
            "mimetype": "image/jpeg",
            "meta": {
                "description_text": "__any_value__",
                "byline": "__any_value__"
            },
            "raw_metadata": {"City": "Montreal"}
        }
        """
        When we post to "/archive"
        """
        {"staged_id": "#upload_staging._id#", "headline": "edited"}
        """
        Then we get response code 201
        And we get existing resource
        """
        {"headline": "edited", "description_text": "__any_value__", "byline": "__any_value__"}
        """

    @auth
    @vocabulary
    Scenario: Staged upload can be committed only once
        When we upload a file "bike.jpg" to "upload_staging"
        When we post to "/archive"
        """
        {"staged_id": "#upload_staging._id#"}
        """
        Then we get response code 201
        When we post to "/archive"
        """
        {"staged_id": "#upload_staging._id#"}
        """
        Then we get response code 404

    @auth
    Scenario: Discard a staged upload
        When we upload a file "bike.jpg" to "upload_staging"
        When we delete "/upload_staging/#upload_staging._id#"
        Then we get OK response
        When we post to "/archive"
        """
        {"staged_id": "#upload_staging._id#"}
        """
        Then we get response code 404

    @auth
    @vocabulary
    Scenario: Video renditions wait for upload confirmation
        When we upload a file "this_week_nasa.mp4" to "upload_staging"
        Then we get new resource
        """
        {"status": "awaiting_confirmation", "metadata_status": "ready"}
        """
        When we patch "/upload_staging/#upload_staging._id#"
        """
        {"confirmed": true}
        """
        Then we get OK response
        When we get "/upload_staging/#upload_staging._id#"
        Then we get existing resource
        """
        {"status": "ready", "confirmed": true, "renditions": {"original": {}}}
        """
        When we post to "/archive"
        """
        {"staged_id": "#upload_staging._id#", "headline": "confirmed video"}
        """
        Then we get response code 201
