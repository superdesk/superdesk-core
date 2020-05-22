Feature: Unpublish content
    
    @auth
    Scenario: Unpublish single item
      Given "desks"
      """
      [{"name": "Sports", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
      """
      And "archive"
      """
      [{"guid": "123", "headline": "test", "_current_version": 0, "state": "fetched",
        "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
        "subject":[{"qcode": "17004000", "name": "Statistics"}],
        "slugline": "test", "type": "text",
        "body_html": "<p>Test Document body</p>\n<p>with a \"quote\"</p>"}]
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}],
        "api_products": ["#products._id#"]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we enqueue published
      Then we assert the content api item "123" is published to subscriber "#subscribers._id#"
      When we get "/items/123"
      
      And we publish "#archive._id#" with "unpublish" type and "unpublished" state
      Then we get OK response
      And we get existing resource
      """
      {"state": "unpublished", "pubstatus": "canceled"}
      """
      When we enqueue published
      Then we assert the content api item "123" is published to subscriber "#subscribers._id#"

      When we get "/publish_queue"
      Then we get list with 4 items
      """
      {
        "_items": [
          {"publishing_action": "unpublished"},
          {"publishing_action": "unpublished"},
          {"publishing_action": "published"},
          {"publishing_action": "published"}
        ]
      }
      """

      When we patch "/archive/#archive._id#"
      """
      {"state": "in_progress"}
      """
      Then we get OK response

      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response

    @auth
    Scenario: Unpublish an item that is in a published package
      Given empty "archive"
      Given "desks"
          """
          [{"name": "test_desk1", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
          """
      And the "validators"
          """
          [{"_id": "publish_composite", "act": "publish", "type": "composite", "schema":{}},
          {"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
          {"_id": "publish_picture", "act": "publish", "type": "picture", "schema":{}}]
          """
      When we post to "archive" with success
          """
          [{
              "headline" : "WA:Navy steps in with WA asylum-seeker boat",
              "guid" : "tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916",
              "state" : "submitted",
              "type" : "text",
              "body_html": "item content",
              "task": {
                  "user": "#CONTEXT_USER_ID#",
                  "status": "todo",
                  "stage": "#desks.incoming_stage#",
                  "desk": "#desks._id#"
              }
          }]
          """
      When we post to "archive" with success
        """
        [{
              "original_source" : "AAP Image/AAP",
              "description_text" : "A test picture",
              "state" : "submitted",
              "headline" : "ABC SHOP CLOSURES",
              "byline" : "PAUL MILLER",
              "source" : "AAP Image",
              "mimetype" : "image/jpeg",
              "type" : "picture",
              "pubstatus" : "usable",
              "task": {
                  "user": "#CONTEXT_USER_ID#",
                  "status": "todo",
                  "stage": "#desks.incoming_stage#",
                  "desk": "#desks._id#"
              },
              "guid" : "urn:newsml:localhost:2015-07-24T15:04:29.589984:af3bef9a-5002-492b-a15a-8b460e69b164",
              "renditions" : {
                  "baseImage" : {
                      "height" : 1400,
                      "media" : "55b078b31d41c8e974d17ecf",
                      "href" : "http://localhost:5000/api/upload/55b078b31d41c8e974d17ecf/raw?_schema=http",
                      "mimetype" : "image/jpeg",
                      "width" : 933
                  }
              },
              "slugline" : "ABC SHOP CLOSURES"
        }]
        """
      When we post to "archive" with success
          """
          [{
              "groups": [
              {
                  "id": "root",
                  "refs": [
                      {
                          "idRef": "main"
                      },
                      {
                          "idRef": "sidebars"
                      }
                  ],
                  "role": "grpRole:NEP"
              },
              {
                  "id": "main",
                  "refs": [
                      {
                          "renditions": {},
                          "slugline": "Boat",
                          "guid": "tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916",
                          "headline": "WA:Navy steps in with WA asylum-seeker boat",
                          "location": "archive",
                          "type": "text",
                          "itemClass": "icls:text",
                          "residRef": "tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916"
                      }
                  ],
                  "role": "grpRole:main"
              },
              {
                  "id": "sidebars",
                  "refs": [
                      {
                          "renditions": {
                              "baseImage": {
                                  "width": 933,
                                  "height": 1400,
                                  "href": "http://localhost:5000/api/upload/55b078b31d41c8e974d17ecf/raw?_schema=http",
                                  "mimetype": "image/jpeg",
                                  "media": "55b078b31d41c8e974d17ecf"
                              }
                          },
                          "slugline": "ABC SHOP CLOSURES",
                          "type": "picture",
                          "guid": "urn:newsml:localhost:2015-07-24T15:04:29.589984:af3bef9a-5002-492b-a15a-8b460e69b164",
                          "headline": "ABC SHOP CLOSURES",
                          "location": "archive",
                          "itemClass": "icls:picture",
                          "residRef": "urn:newsml:localhost:2015-07-24T15:04:29.589984:af3bef9a-5002-492b-a15a-8b460e69b164"
                      }
                  ],
                  "role": "grpRole:sidebars"
              }
          ],
              "task": {
                  "user": "#CONTEXT_USER_ID#",
                  "status": "todo",
                  "stage": "#desks.incoming_stage#",
                  "desk": "#desks._id#"
              },
              "guid" : "compositeitem",
              "headline" : "WA:Navy steps in with WA asylum-seeker boat",
              "state" : "submitted",
              "type" : "composite"
          }]
          """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
      And we post to "/subscribers" with success
          """
          {
          "name":"Channel 3","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
          "products": ["#products._id#"],
          "destinations":[{"name":"Test","format": "ninjs", "delivery_type":"PublicArchive","config":{"recipients":"test@test.com"}}]
          }
          """
      And we publish "compositeitem" with "publish" type and "published" state
      Then we get OK response
      When we publish "tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916" with "unpublish" type and "unpublished" state
      Then we get OK response

    @auth
    Scenario: Unpublish an item with associations
      Given "desks"
      """
      [{"name": "Sports", "members":[{"user":"#CONTEXT_USER_ID#"}]}]
      """
      And "archive"
      """
      [
        {
            "_id": "123",
            "guid": "123",
            "headline": "test",
            "_current_version": 0,
            "state": "fetched",
            "task": {
                "desk": "#desks._id#",
                "stage": "#desks.incoming_stage#",
                "user": "#CONTEXT_USER_ID#"
            },
            "subject": [
                {
                    "qcode": "17004000",
                    "name": "Statistics"
                }
            ],
            "slugline": "test",
            "type": "text",
            "body_html": "<p>Test Document body</p>\n<p>with a \"quote\"</p>",
            "associations": {
                "featuremedia": {
                    "_id": "d7c9bd89-ece1-400b-bccb-14eb49c8013f",
                    "guid": "d7c9bd89-ece1-400b-bccb-14eb49c8013f",
                    "_current_version": 1,
                    "type": "picture",
                    "source": "EPA",
                    "credit": "EPA",
                    "byline": "EPA",
                    "copyrightnotice": "EPA",
                    "headline": "Video headline",
                    "description_text": "Video description text",
                    "firstcreated": "2020-01-08T09:52:09+0000",
                    "versioncreated": "2020-01-08T12:15:05+0000",
                    "mimetype": "image/jpeg",
                    "pubstatus": "usable",
                    "state": "fetched",
                    "format": "HTML",
                    "sign_off": "ADM",
                    "language": "nl",
                    "used": true,
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/5e15c7c7220b7b99ee329a64.jpg",
                            "media": "5e15c7c7220b7b99ee329a64",
                            "mimetype": "image/jpeg",
                            "width": 6336,
                            "height": 4275
                        },
                        "baseImage": {
                            "href": "http://localhost:5000/api/upload-raw/5e15c7c9220b7b99ee329a7d.jpg",
                            "media": "5e15c7c9220b7b99ee329a7d",
                            "mimetype": "image/jpeg",
                            "width": 1400,
                            "height": 944
                        },
                        "thumbnail": {
                            "href": "http://localhost:5000/api/upload-raw/5e15c7c9220b7b99ee329a7f.jpg",
                            "media": "5e15c7c9220b7b99ee329a7f",
                            "mimetype": "image/jpeg",
                            "width": 177,
                            "height": 120
                        },
                        "viewImage": {
                            "href": "http://localhost:5000/api/upload-raw/5e15c7c9220b7b99ee329a81.jpg",
                            "media": "5e15c7c9220b7b99ee329a81",
                            "mimetype": "image/jpeg",
                            "width": 640,
                            "height": 431
                        }
                    }
                },
                "related--1": {
                    "_id": "456",
                    "type": "text"
                }
            }
        },
        {
            "_id": "456",
            "guid": "456",
            "_current_version": 0,
            "headline": "test two",
            "state": "fetched",
            "task": {
                "desk": "#desks._id#",
                "stage": "#desks.incoming_stage#",
                "user": "#CONTEXT_USER_ID#"
            },
            "subject": [
                {
                    "qcode": "17004000",
                    "name": "Statistics"
                }
            ],
            "slugline": "test two",
            "type": "text",
            "body_html": "<p>Second Test Document.</p>"
        },
        {
          "_id": "d7c9bd89-ece1-400b-bccb-14eb49c8013f",
          "guid": "d7c9bd89-ece1-400b-bccb-14eb49c8013f",
          "_current_version": 1,
          "type": "picture",
          "source": "EPA",
          "credit": "EPA",
          "byline": "EPA",
          "copyrightnotice": "EPA",
          "headline": "Video headline",
          "description_text": "Video description text",
          "firstcreated": "2020-01-08T09:52:09+0000",
          "versioncreated": "2020-01-08T12:15:05+0000",
          "mimetype": "image/jpeg",
          "pubstatus": "usable",
          "state": "fetched",
          "format": "HTML",
          "sign_off": "ADM",
          "language": "nl",
          "used": true,
          "renditions": {
              "original": {
                  "href": "http://localhost:5000/api/upload-raw/5e15c7c7220b7b99ee329a64.jpg",
                  "media": "5e15c7c7220b7b99ee329a64",
                  "mimetype": "image/jpeg",
                  "width": 6336,
                  "height": 4275
              },
              "baseImage": {
                  "href": "http://localhost:5000/api/upload-raw/5e15c7c9220b7b99ee329a7d.jpg",
                  "media": "5e15c7c9220b7b99ee329a7d",
                  "mimetype": "image/jpeg",
                  "width": 1400,
                  "height": 944
              },
              "thumbnail": {
                  "href": "http://localhost:5000/api/upload-raw/5e15c7c9220b7b99ee329a7f.jpg",
                  "media": "5e15c7c9220b7b99ee329a7f",
                  "mimetype": "image/jpeg",
                  "width": 177,
                  "height": 120
              },
              "viewImage": {
                  "href": "http://localhost:5000/api/upload-raw/5e15c7c9220b7b99ee329a81.jpg",
                  "media": "5e15c7c9220b7b99ee329a81",
                  "mimetype": "image/jpeg",
                  "width": 640,
                  "height": 431
              }
          }
        }
      ]
      """
      When we get "/archive/"
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
      }
      """
      And we post to "/subscribers" with success
      """
      {
        "name":"Channel 3","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}],
        "api_products": ["#products._id#"]
      }
      """
      And we publish "123" with "publish" type and "published" state
      Then we get OK response

      When we publish "123" with "unpublish" type and "unpublished" state
      Then we get OK response

      When we get "/archive/123/"
      Then we get OK response
      And we get existing resource
      """
      {"state": "unpublished", "pubstatus": "canceled"}
      """

      When we get "/archive/d7c9bd89-ece1-400b-bccb-14eb49c8013f/"
      Then we get OK response
      And we get existing resource
      """
      {"state": "published", "pubstatus": "usable"}
      """
