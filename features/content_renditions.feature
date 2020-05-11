Feature: Create renditions

    @auth
    @vocabulary
    Scenario: Crops generated automatically for pictures
    When we upload a file "bike.jpg" to "archive"
    When we post to "/picture_renditions"
    """
    {
        "item":{
            "_id": 123,
            "renditions":{
                "original":{
                    "media":"#archive.renditions.viewImage.media#",
                    "mimetype": "image/jpeg"
                }
            }
        }
    }
    """
    Then we get response code 201
    Then we get rendition "16-9" with mimetype "image/jpeg"
    Then we get rendition "4-3" with mimetype "image/jpeg"
    Then we get rendition "baseImage" with mimetype "image/jpeg"
    Then we get rendition "original" with mimetype "image/jpeg"
    Then we get rendition "small" with mimetype "image/jpeg"
    Then we get rendition "square" with mimetype "image/jpeg"
    Then we get rendition "thumbnail" with mimetype "image/jpeg"
    Then we get rendition "viewImage" with mimetype "image/jpeg"
    And we fetch a file "#rendition.viewImage.href#"
    And we fetch a file "#rendition.16-9.href#"
    And we get OK response

    @auth
    @vocabulary
    Scenario: Only system crops are generated
      When we upload a file "bike.jpg" to "archive"
      When we post to "/picture_renditions"
      """
      {
          "item": {
              "_id": 123,
              "renditions": {
                  "original": {
                      "media": "#archive.renditions.viewImage.media#",
                      "mimetype": "image/jpeg"
                  }
              }
          },
          "no_custom_crops": true
      }
      """
      Then we get response code 201
      Then we get rendition "baseImage" with mimetype "image/jpeg"
      Then we get rendition "original" with mimetype "image/jpeg"
      Then we get rendition "thumbnail" with mimetype "image/jpeg"
      Then we get rendition "viewImage" with mimetype "image/jpeg"
      And we fetch a file "#rendition.viewImage.href#"
      And we get OK response
