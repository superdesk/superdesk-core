Feature: Fetch Items from Ingest

    @auth
    @provider
    Scenario: Fetch an item and validate metadata set by API
      Given empty "archive"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And ingest from "reuters"
      """
      [{"guid": "tag_reuters.com_2014_newsml_LOVEA6M0L7U2E", "byline": "Chuck Norris", "dateline": {"source": "Reuters"}}]
      """
      When we post to "/ingest/tag_reuters.com_2014_newsml_LOVEA6M0L7U2E/fetch"
      """
      {"desk": "#desks._id#"}
      """
      Then we get new resource
      When we get "/archive?q=#desks._id#"
      Then we get list with 1 items
      """
      {"_items": [
      	{
      		"family_id": "tag_reuters.com_2014_newsml_LOVEA6M0L7U2E",
      		"ingest_id": "tag_reuters.com_2014_newsml_LOVEA6M0L7U2E",
      		"operation": "fetch",
      		"sign_off": "abc",
      		"byline": "Chuck Norris",
      		"dateline": {"source": "Reuters"}
      	}
      ]}
      """


    @auth
    @provider
    Scenario: Fetch an item empty byline and dateline doesn't get populated
      Given empty "archive"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And ingest from "reuters"
      """
      [{"guid": "tag_reuters.com_2014_newsml_LOVEA6M0L7U2E"}]
      """
      When we post to "/ingest/tag_reuters.com_2014_newsml_LOVEA6M0L7U2E/fetch"
      """
      {"desk": "#desks._id#"}
      """
      Then we get new resource
      When we get "/archive?q=#desks._id#"
      Then we get no "byline"
      Then we get no "dateline"


    @auth
    @provider
    Scenario: Fetch an item of type Media and validate metadata set by API
      Given empty "archive"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      When we fetch from "reuters" ingest "tag_reuters.com_0000_newsml_GM1EA7M13RP01:484616934"
      And we post to "/ingest/#reuters.tag_reuters.com_0000_newsml_GM1EA7M13RP01:484616934#/fetch" with success
      """
      {
      "desk": "#desks._id#"
      }
      """
      Then we get "_id"
      When we get "/archive/#_id#"
      Then we get existing resource
      """
      {   "sign_off": "abc",
          "renditions": {
              "baseImage": {"height": 845, "mimetype": "image/jpeg", "width": 1400},
              "original": {"height": 2113, "mimetype": "image/jpeg", "width": 3500},
              "thumbnail": {"height": 120, "mimetype": "image/jpeg", "width": 198},
              "viewImage": {"height": 386, "mimetype": "image/jpeg", "width": 640}
          }
      }
      """

    @auth
    @provider
    Scenario: Fetch a package and validate metadata set by API
      Given empty "ingest"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      When we fetch from "reuters" ingest "tag_reuters.com_2014_newsml_KBN0FL0NM:10"
      And we post to "/ingest/#reuters.tag_reuters.com_2014_newsml_KBN0FL0NM:10#/fetch"
      """
      {
      "desk": "#desks._id#"
      }
      """
      And we get "archive"
      Then we get existing resource
      """
      {
          "_items": [
              {
                  "_current_version": 1,
                  "linked_in_packages": [{}],
                  "state": "fetched",
                  "type": "picture",
                  "sign_off": "abc"
              },
              {
                  "_current_version": 1,
                  "groups": [
                      {
                          "refs": [
                              {"itemClass": "icls:text"},
                              {"itemClass": "icls:picture"},
                              {"itemClass": "icls:picture"},
                              {"itemClass": "icls:picture"}
                          ]
                      },
                      {"refs": [{"itemClass": "icls:text"}]}
                  ],
                  "state": "fetched",
                  "type": "composite",
                  "sign_off": "abc"
              },
              {
                  "_current_version": 1,
                  "linked_in_packages": [{}],
                  "state": "fetched",
                  "type": "picture",
                  "sign_off": "abc"
              },
              {
                  "_current_version": 1,
                  "linked_in_packages": [{}],
                  "state": "fetched",
                  "type": "text",
                  "sign_off": "abc"
              },
              {
                  "_current_version": 1,
                  "linked_in_packages": [{}],
                  "state": "fetched",
                  "type": "picture",
                  "sign_off": "abc"
              },
              {
                  "_current_version": 1,
                  "linked_in_packages": [{}],
                  "state": "fetched",
                  "type": "text",
                  "sign_off": "abc"
              }
          ]
      }
      """

    @auth
    @provider
    Scenario: Fetch same ingest item to a desk twice
      Given empty "archive"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And ingest from "reuters"
      """
      [{"guid": "tag_reuters.com_2014_newsml_LOVEA6M0L7U2E"}]
      """
      When we post to "/ingest/tag_reuters.com_2014_newsml_LOVEA6M0L7U2E/fetch"
      """
      {"desk": "#desks._id#"}
      """
      And we post to "/ingest/tag_reuters.com_2014_newsml_LOVEA6M0L7U2E/fetch"
      """
      {"desk": "#desks._id#"}
      """
      Then we get new resource
      When we get "/archive?q=#desks._id#"
      Then we get list with 2 items
      """
      {"_items": [
              {
                "family_id": "tag_reuters.com_2014_newsml_LOVEA6M0L7U2E",
                "unique_id": 1
               },
              {
                "family_id": "tag_reuters.com_2014_newsml_LOVEA6M0L7U2E",
                "unique_id": 2
              }
              ]}
      """

    @auth
    Scenario: Fetch should fail when invalid ingest id is passed
      Given empty "archive"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And empty "ingest"
      When we post to "/ingest/invalid_id/fetch"
      """
      {
      "desk": "#desks._id#"
      }
      """
      Then we get error 404
      """
      {"_message": "Fail to found ingest item with _id: invalid_id", "_status": "ERR"}
      """

    @auth
    @provider
    Scenario: Fetch should fail when no desk is specified
      Given empty "archive"
      When we fetch from "reuters" ingest "tag_reuters.com_0000_newsml_GM1EA7M13RP01:484616934"
      When we post to "/ingest/tag_reuters.com_0000_newsml_GM1EA7M13RP01:484616934/fetch"
      """
      {}
      """
      Then we get error 400
      """
      {"_issues": {"desk": {"required": 1}}}
      """

    @auth
    @provider
    Scenario: Fetched item should have "in_progress" state when locked and edited
      Given empty "archive"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And ingest from "reuters"
      """
      [{"guid": "tag_reuters.com_2014_newsml_LOVEA6M0L7U2E"}]
      """
      When we post to "/ingest/tag_reuters.com_2014_newsml_LOVEA6M0L7U2E/fetch"
      """
      {"desk": "#desks._id#"}
      """
      Then we get "_id"
      When we post to "/archive/#_id#/lock"
      """
      {}
      """
      And we patch "/archive/#_id#"
      """
      {"headline": "test 2"}
      """
      Then we get existing resource
      """
      {"headline": "test 2", "state": "in_progress", "task": {"desk": "#desks._id#"}}
      """

    @auth
    @provider
    Scenario: User can't fetch content without a privilege
      Given empty "archive"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And ingest from "reuters"
      """
      [{"guid": "tag_reuters.com_2014_newsml_LOVEA6M0L7U2E"}]
      """
      When we login as user "foo" with password "bar" and user type "user"
      """
      {"user_type": "user", "email": "foo.bar@foobar.org"}
      """
      And we post to "/ingest/tag_reuters.com_2014_newsml_LOVEA6M0L7U2E/fetch"
      """
      {"desk": "#desks._id#"}
      """
      Then we get response code 403

    @auth
    Scenario: Use default content profiles when fetching text item
        Given config
        """
        {"DEFAULT_CONTENT_TYPE": "bar"}
        """
        And "ingest"
        """
        [{"_id": "ingest1", "type": "text"}, {"_id": "ingest2", "type": "picture"}]
        """
        And "content_types"
        """
        [{"_id": "foo"}]
        """
        When we get "/ingest/ingest1"
        Then we get existing resource
        """
        {"profile": "bar"}
        """

        When we post to "/desks"
        """
        {"name": "sports", "default_content_profile": "foo", "content_profiles": {"foo": 1}}
        """
        Then we get new resource

        When we post to "/ingest/ingest1/fetch"
        """
        {"desk": "#desks._id#"}
        """
        Then we get new resource
        """
        {"profile": "foo"}
        """

        When we post to "/ingest/ingest2/fetch"
        """
        {"desk": "#desks._id#"}
        """
        Then we get new resource
        """
        {"profile": null}
        """

    @auth
    @provider
    Scenario: Fetch an item from reuters and ensure that dateline and source don't change on publish.
      Given empty "archive"
      And "desks"
      """
      [{"name": "Sports", "source": "AAP"}]
      """
      And the "validators"
      """
        [
        {
            "schema": {},
            "type": "text",
            "act": "publish",
            "_id": "publish_text"
        },
        {
            "_id": "publish_composite",
            "act": "publish",
            "type": "composite",
            "schema": {}
        }
        ]
      """
      And ingest from "reuters"
      """
      [{"guid": "tag_reuters.com_2014_newsml_LOVEA6M0L7U2E"}]
      """
      When we post to "/ingest/tag_reuters.com_2014_newsml_LOVEA6M0L7U2E/fetch" with "fetched_item" and success
      """
      {"desk": "#desks._id#"}
      """
      And we patch "/archive/#fetched_item#"
      """
      {
        "dateline": {
          "date": "2017-01-05T04:00:00+0000",
          "located" : {
              "city" : "Sydney",
              "state" : "NSW",
              "tz" : "Australia/Sydney",
              "country" : "Australia",
              "city_code" : "Sydney",
              "country_code" : "AU",
              "state_code" : "AU.02",
              "dateline" : "city",
              "alt_name" : ""
          }
        }
      }
      """
      Then we get existing resource
      """
      {
        "_current_version": 2,
        "source": "reuters",
        "dateline": {
          "date": "2017-01-05T04:00:00+0000",
          "text": "SYDNEY, Jan 5 reuters -",
          "located" : {
              "city" : "Sydney",
              "state" : "NSW",
              "tz" : "Australia/Sydney",
              "country" : "Australia",
              "city_code" : "Sydney",
              "country_code" : "AU",
              "state_code" : "AU.02",
              "dateline" : "city",
              "alt_name" : ""
          }
        }
      }
      """
      When we post to "/products" with success
      """
      {
        "name":"prod-1","codes":"abc,xyz"
      }
      """
      And we post to "/subscribers" with "digital" and success
      """
      {
        "name":"Channel 1","media_type":"media", "subscriber_type": "digital", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we post to "/subscribers" with "wire" and success
      """
      {
        "name":"Channel 2","media_type":"media", "subscriber_type": "wire", "sequence_num_settings":{"min" : 1, "max" : 10}, "email": "test@test.com",
        "products": ["#products._id#"],
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we publish "#fetched_item#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {
        "_current_version": 3, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"},
        "source": "reuters",
        "dateline": {
          "date": "2017-01-05T04:00:00+0000",
          "text": "SYDNEY, Jan 5 reuters -",
          "located" : {
              "city" : "Sydney",
              "state" : "NSW",
              "tz" : "Australia/Sydney",
              "country" : "Australia",
              "city_code" : "Sydney",
              "country_code" : "AU",
              "state_code" : "AU.02",
              "dateline" : "city",
              "alt_name" : ""
          }
        }
      }
      """
      When we get "/published"
      Then we get existing resource
      """
      {"_items" : [
        {
          "_id": "#fetched_item#", "_current_version": 3, "state": "published", "type": "text","source": "reuters",
          "dateline": {
            "date": "2017-01-05T04:00:00+0000",
            "text": "SYDNEY, Jan 5 reuters -",
            "located" : {
                "city" : "Sydney",
                "state" : "NSW",
                "tz" : "Australia/Sydney",
                "country" : "Australia",
                "city_code" : "Sydney",
                "country_code" : "AU",
                "state_code" : "AU.02",
                "dateline" : "city",
                "alt_name" : ""
            }
          }
        },
        {
          "_id": "#archive.take_package#", "_current_version": 2, "state": "published", "type": "composite", "source": "reuters",
          "dateline": {
            "date": "2017-01-05T04:00:00+0000",
            "text": "SYDNEY, Jan 5 reuters -",
            "located" : {
                "city" : "Sydney",
                "state" : "NSW",
                "tz" : "Australia/Sydney",
                "country" : "Australia",
                "city_code" : "Sydney",
                "country_code" : "AU",
                "state_code" : "AU.02",
                "dateline" : "city",
                "alt_name" : ""
            }
          }
        }
        ]}
      """