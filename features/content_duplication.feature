Feature: Duplication of Content

    Background: Setup data required to test Duplication feature
      Given empty "ingest"
      And the "validators"
      """
      [{"_id": "publish_text", "act": "publish", "type": "text", "schema":{}},
       {"_id": "kill_text", "act": "kill", "type": "text", "schema":{}}]
      """
      And "desks"
      """
      [{"name": "Sports"}]
      """
      And "archive"
      """
      [{  "type":"text", "event_id": "abc123", "headline": "test1", "guid": "123",
          "original_creator": "#CONTEXT_USER_ID#",
          "state": "submitted", "source": "REUTERS", "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body",
          "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"},
          "firstcreated": "2017-10-10T10:10:10+0000",
          "firstpublished": "2017-10-10T12:12:12+0000"
      }]
      """

    @auth @notification
    Scenario: Duplicate a content with versions
      When we patch given
      """
      {"headline": "test2"}
      """
      And we patch latest
      """
      {"headline": "test3"}
      """
      Then we get updated response
      """
      {"headline": "test3", "state": "in_progress", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
      """
      And we get version 3
      When we get "/archive/123?version=all"
      Then we get list with 3 items
      When we post to "/archive/123/duplicate"
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      {"state": "submitted", "_current_version": 4, "source": "AAP",
       "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#", "user": "#CONTEXT_USER_ID#"},
       "original_id": "123",
       "firstcreated": "__now__",
       "versioncreated": "__now__"
      }
      """
      Then there is no "last_production_desk" in task
      And there is no "last_authoring_desk" in task
      And there is no "last_desk" in task
      And there is no "desk_history" in task
      And we get notifications
      """
        [{"event": "content:update", "extra": {"items": {"123": 1}, "desks": {"#desks._id#": 1}, "stages": {"#desks.working_stage#": 1}}, "_created": "__any_value__"}]
      """
      When we get "/archive/#duplicate._id#?version=all"
      Then we get list with 4 items

      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      {"operation": "duplicate"}
      """
      When we get "/archive?q=#desks._id#"
      Then we get list with 2 items

    @auth @notification
    Scenario: Duplicate a content with history
      When we patch given
      """
      {"headline": "test2"}
      """
      And we patch latest
      """
      {"headline": "test3"}
      """
      Then we get updated response
      """
      {"headline": "test3", "state": "in_progress", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
      """
      And we get version 3
      When we get "/archive_history?where=item_id==%22123%22"
      Then we get list with 3 items
      When we post to "/archive/123/duplicate"
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      {"state": "submitted", "_current_version": 4, "source": "AAP",
       "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#", "user": "#CONTEXT_USER_ID#"},
       "original_id": "123"}
      """
      Then there is no "last_production_desk" in task
      And there is no "last_authoring_desk" in task
      And we get notifications
      """
        [{"event": "content:update", "extra": {"items": {"123": 1}, "desks": {"#desks._id#": 1}, "stages": {"#desks.working_stage#": 1}}, "_created": "__any_value__"}]
      """
      When we get "/archive_history?where=item_id==%22#duplicate._id#%22"
      Then we get list with 4 items
      """
      {"_items": [
        {"version": 1, "operation": "create"},
        {"version": 2, "operation": "update"},
        {"version": 3, "operation": "update"},
        {"version": 4, "operation": "duplicated_from"}
      ]}
      """


    @auth
    Scenario: Duplicate a content with history doesn't change the state if it's submitted
      When we post to "/archive/123/duplicate"
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      {"state": "submitted", "_current_version": 1, "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#", "user": "#CONTEXT_USER_ID#"}}
      """
      When we get "/archive/#duplicate._id#?version=all"
      Then we get list with 1 items
      When we get "/archive?q=#desks._id#"
      Then we get list with 2 items

    @auth
    Scenario: Duplicate a content where desk has source
       When we patch "desks/#desks._id#"
       """
       {"source": "FOO"}
       """
       Then we get OK response
       When we post to "/archive/123/duplicate"
       """
       {"desk": "#desks._id#","type": "archive"}
       """
       When we get "/archive/#duplicate._id#"
       Then we get existing resource
       """
       {"state": "submitted", "_current_version": 1, "source": "FOO",
       "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#", "user": "#CONTEXT_USER_ID#"}}
       """
       When we get "/archive/#duplicate._id#?version=all"
       Then we get list with 1 items
       When we get "/archive?q=#desks._id#"
       Then we get list with 2 items

    @auth
    @provider
    Scenario: Duplicate a package
      When we fetch from "reuters" ingest "tag_reuters.com_2014_newsml_KBN0FL0NM:10"
      And we post to "/ingest/#reuters.tag_reuters.com_2014_newsml_KBN0FL0NM:10#/fetch" with success
      """
      {"desk": "#desks._id#"}
      """
      Then we get "_id"
      When we post to "/archive/#_id#/duplicate"
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      When we get "/archive?q=#desks._id#"
      Then we get list with 13 items

    @auth
    Scenario: Duplicate should fail when no desk specified
      When we post to "/archive/123/duplicate"
      """
      {}
      """
      Then we get error 400
      """
      {"_issues": {"desk": {"required": 1}}}
      """

    @auth
    Scenario: Item can be duplicated to a different desk
      When we post to "/desks"
      """
      [{"name": "Finance"}]
      """
      When we post to "/archive/123/duplicate"
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      Then we get OK response
      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      { "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#", "user": "#CONTEXT_USER_ID#"}}
      """

    @auth
    Scenario: Item can be duplicated to a different desk and stage
      When we post to "/desks"
      """
      [{"name": "Finance"}]
      """
      And we post to "/stages"
      """
      [
        {
        "name": "another stage",
        "description": "another stage",
        "task_status": "in_progress",
        "desk": "#desks._id#"
        }
      ]
      """
      And we post to "/archive/123/duplicate"
      """
      {"desk": "#desks._id#","stage": "#stages._id#","type": "archive"}
      """
      Then we get OK response
      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      { "task": {"desk": "#desks._id#", "stage": "#stages._id#", "user": "#CONTEXT_USER_ID#"}}
      """

    @auth
    Scenario: User can't duplicate content without a privilege
      When we login as user "foo" with password "bar" and user type "user"
      """
      {"user_type": "user", "email": "foo.bar@foobar.org"}
      """
      And we post to "/archive/123/duplicate"
      """
      [{"desk": "#desks._id#","type": "archive"}]
      """
      Then we get response code 403

    @auth
    Scenario: Sign off is changed when item is duplicated by another person
      When we patch given
      """
      {"headline": "test2"}
      """
      Then we get updated response
      """
      {"headline": "test2", "state": "in_progress", "sign_off": "abc", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#", "user": "#CONTEXT_USER_ID#"}}
      """
      When we switch user
      And we post to "/archive/123/duplicate"
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      And we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      {"state": "submitted", "sign_off": "foo", "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#"}}
      """

    @auth
    @provider
    Scenario: Duplicate a item in the package doesn't keep the package
      When we post to "archive" with success
        """
        [{"headline" : "WA:Navy steps in with WA asylum-seeker boat", "guid" : "tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916",
          "state" : "submitted", "type" : "text", "body_html": "item content",
          "task": {"user": "#CONTEXT_USER_ID#", "status": "todo", "stage": "#desks.incoming_stage#", "desk": "#desks._id#"}
        }]
        """
      And we post to "archive" with success
      """
        [{
            "groups": [
            {
                "id": "root",
                "refs": [
                    {
                        "idRef": "main"
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
      When we post to "/archive/tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916/duplicate"
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      When we get "/archive/#duplicate._id#"
      Then there is no "linked_in_packages" in response

    @auth
    Scenario: Duplicate a Scheduled Item
      When we patch "/archive/123"
      """
      {"publish_schedule":"#DATE+1#"}
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
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      """
        {"publish_schedule": "#DATE+1#"}
      """
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 3, "state": "scheduled", "operation": "publish"}
      """
      When we post to "/archive/123/duplicate" with success
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      And we get "/archive/#duplicate._id#"
      Then there is no "publish_schedule" in response

    @auth
    Scenario: Duplicate a published item and original item's ID is present in the duplicated item
     Given "published"
         """
         [{"_id":"1","item_id": "123", "state": "published"}]
         """
      When we post to "/archive/#archive._id#/duplicate" with success
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      And we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      {"original_id": "123"}
      """

    @auth @test
    Scenario: Duplicated item will have a new event_id
     When we post to "/archive/123/duplicate" with success
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      And we get "/archive/#duplicate._id#"
      Then the field "event_id" value is not "abc123"

    @auth
    Scenario: Duplicate an Updated, Highlighted and Marked Item
      When we rewrite "123"
      """
      {"desk_id": "#desks._id#"}
      """
      Then we get OK response
      When we get "/archive/123"
      """
      {"rewritten_by": "#REWRITE_ID#"}
      """
      When we post to "highlights"
      """
      {"name": "highlight1", "desks": ["#desks._id#"]}
      """
      And we post to "marked_for_highlights"
      """
      [{"highlights": "#highlights._id#", "marked_item": "123"}]
      """
      And we post to "/marked_for_desks" with success
      """
      [{"marked_desk": "#desks._id#", "marked_item": "#archive._id#"}]
      """
      And we post to "/archive/123/duplicate" with success
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      And we get "/archive/#duplicate._id#"
      Then there is no "rewritten_by" in response
      Then there is no "highlights" in response
      Then there is no "marked_desks" in response
      When we post to "/archive/#REWRITE_ID#/duplicate" with success
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      And we get "/archive/#duplicate._id#"
      Then there is no "rewrite_of" in response



    @auth
    Scenario: Duplicate fails when item state is killed
      When we patch "/archive/123"
      """
      {"publish_schedule":"#DATE+1#"}
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
        "destinations":[{"name":"Test","format": "nitf", "delivery_type":"email","config":{"recipients":"test@test.com"}}]
      }
      """
      And we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      When we publish "#archive._id#" with "kill" type and "killed" state
      Then we get OK response
      When we post to "/archive/123/duplicate"
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      Then we get error 412
      """
      {"_message": "Workflow transition is invalid."}
      """

    @auth
    Scenario: Duplicate an expired published item and publish the duplicated item
      When we publish "#archive._id#" with "publish" type and "published" state
      Then we get OK response
      And we get existing resource
      """
      {"_current_version": 2, "state": "published", "task":{"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}
      """
      When we get "/published"
      Then we get list with 1 items
      """
      {"_items" : [
        {"_id": "123", "_current_version": 1, "state": "published", "type": "text", "_current_version": 2}
        ]
      }
      """
      When we enqueue published
      When we transmit items
      And run import legal publish queue
      And we expire items
      """
      ["123"]
      """
      And we get "/published"
      Then we get list with 0 items
      When we enqueue published
      When we get "/publish_queue"
      Then we get list with 0 items
      When we get "/archived"
      Then we get list with 1 items
      """
      {"_items" : [
        {"item_id": "123", "_current_version": 1, "state": "published", "type": "text", "_current_version": 2}
        ]
      }
      """
      When we post to "/archive/#archive._id#/duplicate" with success
      """
      {"desk": "#desks._id#", "type": "archived", "item_id": "123"}
      """
      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      {"state": "submitted", "_current_version": 3, "source": "AAP",
       "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#", "user": "#CONTEXT_USER_ID#"},
       "original_id": "123", "headline": "test1", "type": "text"}
      """
      Then we ensure that archived schema extra fields are not present in duplicated item
      When we get "/published"
      Then we get list with 0 items
      When we publish "#duplicate._id#" with "publish" type and "published" state
      Then we get OK response
      When we get "/published"
      Then we get list with 1 items
      """
      {"_items" : [
        {"_current_version": 4, "state": "published", "type": "text"}]
      }
      """

    @auth
    Scenario: Duplicate a archived item and the original ID of the archived item should be copied to duplicated item and the latest version of archived item should be picked
      Given "archived"
         """
         [{  "_id": "123_1", "state": "published", "type":"text", "headline": "test1", "guid": "123_1", "item_id": "123", "original_creator": "#CONTEXT_USER_ID#",
          "source": "REUTERS", "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body", "_current_version": 1, "archived_id": "123:1",
          "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#", "user": "#CONTEXT_USER_ID#"}},
          {  "_id": "123_2", "state": "published", "type":"text", "headline": "test2", "guid": "123_2", "item_id": "123", "original_creator": "#CONTEXT_USER_ID#",
          "source": "REUTERS", "subject":[{"qcode": "17004000", "name": "Statistics"}],
          "body_html": "Test Document body", "_current_version": 2, "archived_id": "123:2",
          "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#", "user": "#CONTEXT_USER_ID#"}
         }]
         """
      When we get "/archived"
      Then we get list with 2 items
      When we post to "/archive/123_1/duplicate" with success
      """
      {"desk": "#desks._id#", "type": "archived", "item_id": "123"}
      """
      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      {"state": "submitted", "_current_version": 3, "source": "AAP",
       "task": {"desk": "#desks._id#", "stage": "#desks.working_stage#", "user": "#CONTEXT_USER_ID#"},
       "original_id": "123", "headline": "test2"}
      """
      Then we ensure that archived schema extra fields are not present in duplicated item

    @auth
    Scenario: Item can be duplicated to a different desk and stage with a desk source
      When we post to "/desks"
      """
      [{"name": "Finance", "source": "XXX"}]
      """
      And we post to "/stages"
      """
      [
        {
        "name": "another stage",
        "description": "another stage",
        "task_status": "in_progress",
        "desk": "#desks._id#"
        }
      ]
      """
      And we post to "/archive/123/duplicate"
      """
      {"desk": "#desks._id#","stage": "#stages._id#","type": "archive"}
      """
      Then we get OK response
      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      { "task": {"desk": "#desks._id#", "stage": "#stages._id#", "user": "#CONTEXT_USER_ID#"}, "source": "XXX"}
      """

    @auth
    Scenario: Ingested agency item can be duplicated to a different desk and stage with a desk source keeps original source
      Given "ingest_providers"
      """
      [{"name": "agency", "source": "YYY"}]
      """
      When we patch "/archive/123"
      """
      {"ingest_provider": "#ingest_providers._id#", "source": "YYY"}
      """
      And we post to "/desks"
      """
      [{"name": "Finance", "source": "XXX"}]
      """
      And we post to "/stages"
      """
      [
        {
        "name": "another stage",
        "description": "another stage",
        "task_status": "in_progress",
        "desk": "#desks._id#"
        }
      ]
      """
      And we post to "/archive/123/duplicate"
      """
      {"desk": "#desks._id#","stage": "#stages._id#","type": "archive"}
      """
      Then we get OK response
      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      { "task": {"desk": "#desks._id#", "stage": "#stages._id#", "user": "#CONTEXT_USER_ID#"}, "source": "YYY"}
      """

    @auth @test
    Scenario: Duplicated item with SMS flag will have be cleared
      When we patch given
      """
      {"flags": {"marked_for_sms": true}, "sms_message": "Test SMS"}
      """
      When we post to "/archive/123/duplicate" with success
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      When we get "/archive/#duplicate._id#"
      Then we get existing resource
      """
      { "flags": {"marked_for_sms" : false}}
      """

    @auth
    Scenario: Planning assignment is removed from an item on duplication
      When we patch given
      """
      {"assignment_id": "1234"}
      """
      When we post to "/archive/123/duplicate" with success
      """
      {"desk": "#desks._id#","type": "archive"}
      """
      When we get "/archive/#duplicate._id#"
      Then we get "assignment_id" does not exist
