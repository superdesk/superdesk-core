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
    Scenario: Fetch an item and it fetches embedded items
      Given empty "archive"
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And ingest from "reuters"
      """
      [{
          "_id" : "urn:newsml:localhost:5000:2019-03-31T20:37:42.832355:9e339340-11c5-43f5-8314-3c6088bbe562",
          "description_text" : "Oil prices edged up on Monday, supported by the first fall in US drilling activity in month.",
          "headline" : "Financial Markets",
          "versioncreated" : "2019-03-31T09:37:42.000Z",
          "copyrightholder" : "Australian Associated Press",
          "pubstatus" : "usable",
          "place" : [
              {
                  "qcode" : "US",
                  "name" : "US"
              }
          ],
          "anpa_category" : [
              {
                  "qcode" : "f",
                  "name" : "Finance"
              }
          ],
          "byline" : "Bebeto Matthews",
          "genre" : [
              {
                  "qcode" : "Article",
                  "name" : "Article (news)"
              }
          ],
          "firstcreated" : "2015-07-08T15:46:07.000Z",
          "flags" : {
              "marked_for_legal" : false,
              "marked_archived_only" : false,
              "marked_for_sms" : false,
              "marked_for_not_publication" : false
          },
          "type" : "picture",
          "body_text" : "Oil markets something",
          "source" : "NINJS",
          "renditions" : {
              "viewImage" : {
                  "width" : 640,
                  "media" : "5ca08a675f627dc02f16a39a",
                  "mimetype" : "image/jpeg",
                  "height" : 490,
                  "href" : "http://localhost:5000/api/upload-raw/5ca08a675f627dc02f16a39a.jpg"
              },
              "thumbnail" : {
                  "width" : 156,
                  "media" : "5ca08a675f627dc02f16a39c",
                  "mimetype" : "image/jpeg",
                  "height" : 120,
                  "href" : "http://localhost:5000/api/upload-raw/5ca08a675f627dc02f16a39c.jpg"
              },
              "original" : {
                  "width" : 800,
                  "media" : "5ca08a665f627dc02f16a396",
                  "mimetype" : "image/jpeg",
                  "height" : 614,
                  "href" : "http://localhost:5000/api/upload-raw/5ca08a665f627dc02f16a396.jpg"
              },
              "baseImage" : {
                  "width" : 1400,
                  "media" : "5ca08a665f627dc02f16a398",
                  "mimetype" : "image/jpeg",
                  "height" : 1074,
                  "href" : "http://localhost:5000/api/upload-raw/5ca08a665f627dc02f16a398.jpg"
              }
          },
          "copyrightnotice" : "AAP content is owned by or licensed to Australian Associated Press Pty Limited (AAP) and is\r\ncopyright protected.  AAP content is published on an \"as is\" basis for personal use only and\r\nmust not be copied, republished, rewritten, resold or redistributed, whether by caching,\r\nframing or similar means, without AAP's prior written permission.  AAP and its licensors\r\nare not liable for any loss, through negligence or otherwise, resulting from errors or\r\nomissions in or reliance on AAP content.  The globe symbol and \"AAP\" are registered trade marks.\r\nFurther this AAP content is supplied to the direct recipient pursuant to an Information Supply\r\nAgreement with AAP (AAP Information Supply Agreement).  The direct recipient has a non-exclusive,\r\nnon-transferable right to display this AAP content in accordance with and subject to the\r\nterms of the AAP Information Supply Agreement.",
          "alt_text" : "Oil markets something",
          "guid" : "20170809001313906811",
          "usageterms" : "The direct recipient must comply with the limitations specified in the AAP Information\r\nSupply Agreement relating to the AAP content including, without limitation, not permitting\r\nredistribution and storage of the content (outside the terms of the Agreement) and not\r\npermitting deep hyperlinking to the content, framing of the content on a web site,\r\nposting the content to usenet newsgroups or facilitating such actions.",
          "priority" : 3,
          "ingest_provider" : "5ca08a665f627dc02f16a38a",
          "ednote" : "WEDNESDAY, JULY 8, 2015, FILE PHOTO",
          "operation" : "create",
          "urgency" : 3,
          "family_id" : "urn:newsml:localhost:5000:2019-03-31T20:37:42.832355:9e339340-11c5-43f5-8314-3c6088bbe562",
          "slugline" : "GLOBAL-OIL",
          "_etag" : "2a7a9e50489fe061cca9b02976a5dea9fb21f300",
          "mimetype" : "image/jpeg",
          "state" : "ingested",
          "subject" : [
              {
                  "qcode" : "04005004",
                  "name" : "oil and gas - upstream activities"
              },
              {
                  "qcode" : "04000000",
                  "name" : "economy, business and finance"
              },
              {
                  "qcode" : "04005000",
                  "name" : "energy and resource"
              }
          ],
          "unique_id" : 1,
          "original_source" : "AAP",
          "language" : "en",
          "unique_name" : "#1",
          "ingest_provider_sequence" : "1",
          "format" : "HTML",
          "expiry" : "2019-04-02T09:37:42.000Z"
      }, {
          "_id" : "urn:newsml:localhost:5000:2019-03-31T20:37:43.126066:07067129-d906-412d-92c5-4a72d9796a64",
          "description_text" : "Oil prices edged up on Monday, supported by the first fall in US drilling activity in month.",
          "headline" : "Oil prices edge up on first drop in US drilling in months",
          "versioncreated" : "2019-03-31T09:37:42.000Z",
          "copyrightholder" : "Australian Associated Press",
          "format" : "HTML",
          "pubstatus" : "usable",
          "place" : [
              {
                  "qcode" : "US",
                  "name" : "US"
              }
          ],
          "anpa_category" : [
              {
                  "qcode" : "f",
                  "name" : "Finance"
              }
          ],
          "byline" : "By Henning Gloystein",
          "genre" : [
              {
                  "qcode" : "Article",
                  "name" : "Article (news)"
              }
          ],
          "firstcreated" : "2017-07-03T01:38:13.000Z",
          "flags" : {
              "marked_for_legal" : false,
              "marked_archived_only" : false,
              "marked_for_sms" : false,
              "marked_for_not_publication" : false
          },
          "type" : "text",
          "source" : "NINJS",
          "copyrightnotice" : "AAP content is owned by or licensed to Australian Associated Press Pty Limited (AAP) and is\r\ncopyright protected.  AAP content is published on an \"as is\" basis for personal use only and\r\nmust not be copied, republished, rewritten, resold or redistributed, whether by caching,\r\nframing or similar means, without AAP's prior written permission.  AAP and its licensors\r\nare not liable for any loss, through negligence or otherwise, resulting from errors or\r\nomissions in or reliance on AAP content.  The globe symbol and \"AAP\" are registered trade marks.\r\nFurther this AAP content is supplied to the direct recipient pursuant to an Information Supply\r\nAgreement with AAP (AAP Information Supply Agreement).  The direct recipient has a non-exclusive,\r\nnon-transferable right to display this AAP content in accordance with and subject to the\r\nterms of the AAP Information Supply Agreement.",
          "unique_name" : "#2",
          "abstract" : "Oil prices edged up on Monday, supported by the first fall in US drilling activity in month.",
          "guid" : "tag:localhost:2017:7ca07622-3b19-4d61-8daf-18500412d46b",
          "usageterms" : "The direct recipient must comply with the limitations specified in the AAP Information\r\nSupply Agreement relating to the AAP content including, without limitation, not permitting\r\nredistribution and storage of the content (outside the terms of the Agreement) and not\r\npermitting deep hyperlinking to the content, framing of the content on a web site,\r\nposting the content to usenet newsgroups or facilitating such actions.",
          "priority" : 3,
          "ingest_provider" : "5ca08a665f627dc02f16a38a",
          "operation" : "create",
          "urgency" : 3,
          "family_id" : "urn:newsml:localhost:5000:2019-03-31T20:37:43.126066:07067129-d906-412d-92c5-4a72d9796a64",
          "slugline" : "TEST GLOBAL-OIL",
          "_etag" : "1a663fffe2a2cbc711b7178428676aa04ed3dca5",
          "associations" : {
              "embedded216742513" : {
                  "description_text" : "Oil prices edged up on Monday, supported by the first fall in US drilling activity in month.",
                  "urgency" : 3,
                  "versioncreated" : "2017-08-24T01:56:56.000Z",
                  "copyrightholder" : "Australian Associated Press",
                  "pubstatus" : "usable",
                  "genre" : [
                      {
                          "code" : "Article",
                          "name" : "Article (news)"
                      }
                  ],
                  "byline" : "Bebeto Matthews",
                  "place" : [
                      {
                          "code" : "US",
                          "name" : "US"
                      }
                  ],
                  "firstcreated" : "2015-07-08T15:46:07+0000",
                  "version" : "2",
                  "body_text" : "Oil markets something",
                  "source" : "AAP",
                  "_id" : "urn:newsml:localhost:5000:2019-03-31T20:37:42.832355:9e339340-11c5-43f5-8314-3c6088bbe562",
                  "renditions" : {
                      "viewImage" : {
                          "width" : 640,
                          "media" : "5ca08a675f627dc02f16a39a",
                          "mimetype" : "image/jpeg",
                          "href" : "http://localhost:5000/api/upload-raw/5ca08a675f627dc02f16a39a.jpg",
                          "height" : 490
                      },
                      "thumbnail" : {
                          "width" : 156,
                          "media" : "5ca08a675f627dc02f16a39c",
                          "mimetype" : "image/jpeg",
                          "href" : "http://localhost:5000/api/upload-raw/5ca08a675f627dc02f16a39c.jpg",
                          "height" : 120
                      },
                      "original" : {
                          "width" : 3489,
                          "height" : 2296,
                          "mimetype" : "image/jpeg",
                          "poi" : {
                              "y" : 1193,
                              "x" : 2128
                          },
                          "media" : "5ca08a675f627dc02f16a39f",
                          "href" : "http://localhost:5000/api/upload-raw/5ca08a675f627dc02f16a39f.jpg"
                      },
                      "baseImage" : {
                          "width" : 1400,
                          "height" : 921,
                          "mimetype" : "image/jpeg",
                          "poi" : {
                              "y" : 478,
                              "x" : 854
                          },
                          "media" : "5ca08a675f627dc02f16a3a2",
                          "href" : "http://localhost:5000/api/upload-raw/5ca08a675f627dc02f16a3a2.jpg"
                      }
                  },
                  "copyrightnotice" : "AAP content is owned by or licensed to Australian Associated Press Pty Limited (AAP) and is\r\ncopyright protected.  AAP content is published on an \"as is\" basis for personal use only and\r\nmust not be copied, republished, rewritten, resold or redistributed, whether by caching,\r\nframing or similar means, without AAP's prior written permission.  AAP and its licensors\r\nare not liable for any loss, through negligence or otherwise, resulting from errors or\r\nomissions in or reliance on AAP content.  The globe symbol and \"AAP\" are registered trade marks.\r\nFurther this AAP content is supplied to the direct recipient pursuant to an Information Supply\r\nAgreement with AAP (AAP Information Supply Agreement).  The direct recipient has a non-exclusive,\r\nnon-transferable right to display this AAP content in accordance with and subject to the\r\nterms of the AAP Information Supply Agreement.",
                  "alt_text" : "Oil markets something",
                  "guid" : "20170809001313906811",
                  "usageterms" : "The direct recipient must comply with the limitations specified in the AAP Information\r\nSupply Agreement relating to the AAP content including, without limitation, not permitting\r\nredistribution and storage of the content (outside the terms of the Agreement) and not\r\npermitting deep hyperlinking to the content, framing of the content on a web site,\r\nposting the content to usenet newsgroups or facilitating such actions.",
                  "priority" : 3,
                  "ednote" : "WEDNESDAY, JULY 8, 2015, FILE PHOTO",
                  "headline" : "Financial Markets",
                  "slugline" : "GLOBAL-OIL",
                  "service" : [
                      {
                          "code" : "f",
                          "name" : "Finance"
                      }
                  ],
                  "mimetype" : "image/jpeg",
                  "state" : "ingested",
                  "subject" : [
                      {
                          "code" : "04005004",
                          "name" : "oil and gas - upstream activities"
                      }
                  ],
                  "type" : "picture",
                  "language" : "en",
                  "description_html" : "<p>Oil prices edged up on Monday, supported by the first fall in US drilling activity in month.</p>"
              }
          },
          "profile" : "ContentProfile",
          "word_count" : 312,
          "state" : "ingested",
          "subject" : [
              {
                  "qcode" : "04005004",
                  "name" : "oil and gas - upstream activities"
              },
              {
                  "qcode" : "04000000",
                  "name" : "economy, business and finance"
              },
              {
                  "qcode" : "04005000",
                  "name" : "energy and resource"
              }
          ],
          "unique_id" : 2,
          "original_source" : "Reuters",
          "language" : "en",
          "dateline" : {
              "located" : {
                  "city" : "Singapore"
              }
          },
          "ingest_provider_sequence" : "2",
          "body_html" : "<p>Oil prices edged up on Monday,\nsupported by the first autumn in US drilling activity in months,\nalthough rising output from OPEC despite a pledge to cut\nsupplies capped gains.<br/></p><p>Brent crude futures added 6 cents or 0.1 per cent to\n$48.83 per barrel by 0137 GMT, after jumping 5 per cent last week\nfor the first gain in six weeks.</p><p>US West Texas Intermediate (WTI) crude futures rose\n15 cents, or 0.3 per cent, to $46.19 per barrel after a more than\n7 per cent gain last week from depressed levels.</p><p>Traders said US prices were relatively stronger than Brent\nafter US drilling activity fell for the first time since\nJanuary. Sentiment for the global Brent benchmark was more\nsubdued due to rising output from within the the Organisation of\nthe Petroleum Exporting Countries (OPEC).</p><p>\"For the first time in 23 weeks, the number of drill rigs\noperating in the US fell, down 2 to 756,\" ANZ bank said on\nMonday, but added that \"this exuberance may be tempered by news\nover the weekend that Libya oil production hit another record.\"</p><p>Despite the drop, the total rig count was still more than\ndouble the 341 rigs in the same week a year ago, according to\nenergy services firm Baker Hughes Inc.</p><p>The slight cut in US drilling for new production was met\nby a rise in output from within OPEC in June, up by 280,000\nbarrels per day (bpd) to an estimated 2017 high of 32.72 million\nbpd despite the group's pledge to hold back production in an\neffort to tighten the market.</p><p>OPEC's high output is largely down to rising production from\nmembers Nigeria and Libya, which were exempted from the output\ncuts, and whose surge in supplies has undermined efforts by\nother members like Saudi Arabia to restrict supplies.</p><p>(Reporting by Henning Gloystein; Editing by Richard Pullin)</p>",
          "expiry" : "2019-04-02T09:37:42.000Z"
      }]
      """
      When we post to "/ingest/urn:newsml:localhost:5000:2019-03-31T20:37:43.126066:07067129-d906-412d-92c5-4a72d9796a64/fetch"
      """
      {"desk": "#desks._id#"}
      """
      Then we get new resource
      When we get "/archive?q=#desks._id#"
      Then we get list with 2 items
      """
      {"_items": [
      	{
      		"family_id": "urn:newsml:localhost:5000:2019-03-31T20:37:43.126066:07067129-d906-412d-92c5-4a72d9796a64",
      		"ingest_id": "tag:localhost:2017:7ca07622-3b19-4d61-8daf-18500412d46b",
      		"operation": "fetch",
      		"sign_off": "abc",
      		"slugline": "TEST GLOBAL-OIL",
      		"associations" : {
              "embedded216742513" : {
                  "description_text" : "Oil prices edged up on Monday, supported by the first fall in US drilling activity in month."
               }
            },
            "refs": [
                {
                    "key": "embedded216742513",
                    "type": "picture"
                }
            ]
      	}, {
      		"family_id": "urn:newsml:localhost:5000:2019-03-31T20:37:42.832355:9e339340-11c5-43f5-8314-3c6088bbe562",
      		"type": "picture"
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
      {"_message": "Failed to find ingest item with _id: invalid_id", "_status": "ERR"}
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
        {"profile": "bar"}
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
        "name":"prod-1","codes":"abc,xyz", "product_type": "both"
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
        }
        ]}
      """
