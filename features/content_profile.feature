Feature: Content Profile

    @auth
    Scenario: User can create profile
        When we get "content_types"
        Then we get list with 0 items

        When we post to "content_types"
        """
        {"_id": "foo", "label": "Foo", "description": "Foo info"}
        """

        Then we get new resource
        """
        {
            "_id": "foo",
            "label": "Foo",
            "enabled": false,
            "created_by": "#CONTEXT_USER_ID#",
            "updated_by": "#CONTEXT_USER_ID#"
        }
        """

    @auth
    Scenario: User can update profile
        Given "content_types"
        """
        [{"_id": "foo", "label": "Foo"}]
        """
        When we patch "content_types/foo"
        """
        {"label": "Bar", "description": "Bar", "priority": 0, "enabled": true}
        """
        Then we get updated response
        """
        {"updated_by": "#CONTEXT_USER_ID#"}
        """

    @auth
    Scenario: Content profile name should be unique
        Given "content_types"
        """
        [{"_id": "foo", "label": "Foo"}]
        """
        When we post to "content_types"
        """
        [{"_id": "foo2", "label": "Foo"}]
        """
        Then we get error 400

    @auth
    Scenario: User can get extended profile with default values

        When we post to "content_types"
        """
        {"_id": "foo", "label": "Foo"}
        """
        Then we get new resource
        """
        {
            "_id": "foo",
            "label": "Foo",
            "enabled": false,
            "created_by": "#CONTEXT_USER_ID#",
            "updated_by": "#CONTEXT_USER_ID#"
        }
        """

        When we get "/content_types/#content_types._id#?edit=true"
        Then we get existing resource
        """
        {
            "_id": "foo",
            "label": "Foo",
            "enabled": false,
            "created_by": "#CONTEXT_USER_ID#",
            "updated_by": "#CONTEXT_USER_ID#",
            "schema": {
                "slugline": {"maxlength": 24, "type": "string"},
                "genre": {"type": "list"},
                "anpa_take_key": {},
                "place": {"type": "list"},
                "priority": {},
                "anpa_category": {"type": "list"},
                "subject": {
                  "type": "list",
                  "required": true,
                  "mandatory_in_list": {"scheme": {}},
                  "schema": {
                     "type": "dict",
                     "schema": {
                        "name": {},
                        "qcode": {},
                        "scheme": {
                           "type": "string",
                           "required": true,
                           "allowed": ["subject"]
                        },
                        "service": {"nullable": true},
                        "parent": {"nullable": true}
                      }
                  }
                },
                "company_codes": {"type": "list"},
                "ednote": {},
                "headline": {"maxlength": 64, "type": "string"},
                "sms": null,
                "abstract": {"maxlength": 160, "type": "string"},
                "byline": {"type": "string"},
                "dateline": {"type": "dict"},
                "body_html": {},
                "footer": null,
                "body_footer": null,
                "sign_off": {"type": "string"},
                "media": {},
                "media_description": {}
            },
            "editor": {
                "slugline": {"order": 1, "sdWidth": "full", "enabled": true},
                "genre": {"order": 2, "sdWidth": "half", "enabled": true},
                "anpa_take_key": {"order": 3, "sdWidth": "half", "enabled": false},
                "place": {"order": 4, "sdWidth": "half", "enabled": true},
                "priority": {"order": 5, "sdWidth": "quarter", "enabled": true},
                "anpa_category": {"order": 7, "sdWidth": "full", "enabled": true},
                "subject": {"order": 8, "sdWidth": "full", "enabled": true},
                "company_codes": {"order": 9, "sdWidth": "full", "enabled": false},
                "ednote": {"order": 10, "sdWidth": "full", "enabled": true},
                "headline": {"order": 11, "formatOptions": ["underline", "anchor", "bold", "removeFormat"], "enabled": true},
                "sms": {"order": 12, "enabled": false},
                "abstract": {"order": 13, "formatOptions": ["bold", "italic", "underline", "anchor", "removeFormat"], "enabled": true},
                "byline": {"order": 14, "enabled": true},
                "dateline": {"order": 15, "enabled": true},
                "body_html": {
                    "order": 16,
                    "formatOptions": ["h2", "bold", "italic", "underline", "quote", "anchor", "embed", "picture", "removeFormat"],
                    "enabled": true
                },
                "footer": {"order": 17, "enabled": false},
                "body_footer": {"order": 18, "enabled": false},
                "sign_off": {"order": 19, "enabled": true},
                "media": {"enabled": true},
                "media_description": {"enabled": true}
            }
        }
        """


    @auth
    Scenario: User can get profile with extended values

        When we post to "content_types"
        """
        {
            "_id": "foo",
            "label": "Foo",
            "schema": {
                "slugline": {"maxlength": 24, "type": "string"}
            },
            "editor": {
                "slugline": {"order": 1, "sdWidth": "full", "enabled": true}
            }
        }
        """
        Then we get new resource
        """
        {
            "_id": "foo",
            "label": "Foo",
            "enabled": false,
            "created_by": "#CONTEXT_USER_ID#",
            "updated_by": "#CONTEXT_USER_ID#",
            "schema": {
                "slugline": {"maxlength": 24, "type": "string"}
            },
            "editor": {
                "slugline": {"order": 1, "sdWidth": "full", "enabled": true}
            }
        }
        """

        When we get "/content_types/#content_types._id#?edit=true"
        Then we get existing resource
        """
        {
            "_id": "foo",
            "label": "Foo",
            "enabled": false,
            "created_by": "#CONTEXT_USER_ID#",
            "updated_by": "#CONTEXT_USER_ID#",
            "schema": {
                "slugline": {"maxlength": 24, "type": "string"},
                "genre": {"type": "list"},
                "anpa_take_key": {},
                "place": {"type": "list"},
                "priority": {},
                "anpa_category": {"type": "list"},
                "subject": {
                  "type": "list",
                  "required": true,
                  "mandatory_in_list": {"scheme": {}},
                  "schema": {
                     "type": "dict",
                     "schema": {
                        "name": {},
                        "qcode": {},
                        "scheme": {
                           "type": "string",
                           "required": true,
                           "allowed": ["subject"]
                        },
                        "service": {"nullable": true},
                        "parent": {"nullable": true}
                      }
                  }
                },
                "company_codes": {"type": "list"},
                "ednote": {},
                "headline": {"maxlength": 64, "type": "string"},
                "sms": null,
                "abstract": {"maxlength": 160, "type": "string"},
                "byline": {"type": "string"},
                "dateline": {"type": "dict"},
                "body_html": {},
                "footer": null,
                "body_footer": null,
                "sign_off": {"type": "string"},
                "media": {},
                "media_description": {}
            },
            "editor": {
                "slugline": {"order": 1, "sdWidth": "full", "enabled": true},
                "genre": {"order": 2, "sdWidth": "half", "enabled": false},
                "anpa_take_key": {"order": 3, "sdWidth": "half", "enabled": false},
                "place": {"order": 4, "sdWidth": "half", "enabled": false},
                "priority": {"order": 5, "sdWidth": "quarter", "enabled": false},
                "anpa_category": {"order": 7, "sdWidth": "full", "enabled": false},
                "subject": {"order": 8, "sdWidth": "full", "enabled": false},
                "company_codes": {"order": 9, "sdWidth": "full", "enabled": false},
                "ednote": {"order": 10, "sdWidth": "full", "enabled": false},
                "headline": {"order": 11, "formatOptions": ["underline", "anchor", "bold", "removeFormat"], "enabled": false},
                "sms": {"order": 12, "enabled": false},
                "abstract": {"order": 13, "formatOptions": ["bold", "italic", "underline", "anchor", "removeFormat"], "enabled": false},
                "byline": {"order": 14, "enabled": false},
                "dateline": {"order": 15, "enabled": false},
                "body_html": {
                    "order": 16,
                    "formatOptions": ["h2", "bold", "italic", "underline", "quote", "anchor", "embed", "picture", "removeFormat"],
                    "enabled": false
                },
                "footer": {"order": 17, "enabled": false},
                "body_footer": {"order": 18, "enabled": false},
                "sign_off": {"order": 19, "enabled": false},
                "media": {"enabled": false},
                "media_description": {"enabled": false}
            }
        }
        """

    @auth
    Scenario: User can get profile with default extended custom values
        Given "vocabularies"
        """
        [
          {
            "_id": "genre_custom",
            "display_name": "Genre",
            "type": "manageable",
            "service": {"all": 1},
            "single_value": true,
            "schema_field": "genre",
            "dependent": 1,
            "items": [
                {"is_active": true, "name": "Nyheter", "qcode": "Nyheter", "service": {"n": 1, "j": 1, "e": 1, "t": 1, "m": 1, "s": 1, "d": 1, "o": 1, "p": 1, "k": 1}},
                {"is_active": true, "name": "Faktaboks", "qcode": "Faktaboks", "service": {"n": 1}}
            ]
          },
          {
            "_id": "category",
            "display_name": "Category",
            "type": "manageable",
            "service": {"all": 1},
            "single_value": true,
            "dependent": 1,
            "items": [
                {"is_active": true, "name": "Innenriks", "qcode": "Innenriks", "service": {"n": 1, "s": 1, "e": 1, "t": 1, "m": 1, "j": 1, "i": 1}},
                {"is_active": true, "name": "Utenriks", "qcode": "Utenriks", "service": {"n": 1, "s": 1, "e": 1, "t": 1, "m": 1, "i": 1}}
            ]
          },
          {
            "_id": "subject_custom",
            "display_name": "Subject",
            "type": "manageable",
            "service": {"all": 1},
            "schema_field": "subject",
            "dependent": 0,
            "items": [
                {"is_active": true, "name": "Kultur og underholdning", "qcode": "01000000", "parent": null},
                {"is_active": true, "name": "Kriminalitet og rettsvesen", "qcode": "02000000", "parent": null}
            ]
          }
        ]
        """

        When we post to "content_types"
        """
        {
            "_id": "foo",
            "label": "Foo"
        }
        """
        Then we get new resource
        """
        {
            "_id": "foo",
            "label": "Foo",
            "enabled": false,
            "created_by": "#CONTEXT_USER_ID#",
            "updated_by": "#CONTEXT_USER_ID#"
        }
        """

        When we get "/content_types/#content_types._id#?edit=true"
        Then we get existing resource
        """
        {
            "_id": "foo",
            "label": "Foo",
            "enabled": false,
            "created_by": "#CONTEXT_USER_ID#",
            "updated_by": "#CONTEXT_USER_ID#",
            "schema": {
                "slugline": {"maxlength": 24, "type": "string"},
                "genre": {"type": "list"},
                "anpa_take_key": {},
                "place": {"type": "list"},
                "priority": {},
                "anpa_category": {"type": "list"},
                "subject": {
                  "type": "list",
                  "required": true,
                  "mandatory_in_list": {"scheme": {}},
                  "schema": {
                     "type": "dict",
                     "schema": {
                        "name": {},
                        "qcode": {},
                        "scheme": {
                           "type": "string",
                           "required": true,
                           "allowed": ["subject_custom", "category"]
                        },
                        "service": {"nullable": true},
                        "parent": {"nullable": true}
                      }
                  }
                },
                "company_codes": {"type": "list"},
                "ednote": {},
                "headline": {"maxlength": 64, "type": "string"},
                "sms": null,
                "abstract": {"maxlength": 160, "type": "string"},
                "byline": {"type": "string"},
                "dateline": {"type": "dict"},
                "body_html": {},
                "footer": null,
                "body_footer": null,
                "sign_off": {"type": "string"},
                "media": {},
                "media_description": {}
            },
            "editor": {
                "slugline": {"order": 1, "sdWidth": "full", "enabled": true},
                "genre_custom": {"order": 2, "sdWidth": "half", "enabled": true},
                "category": {"enabled": true},
                "anpa_take_key": {"order": 3, "sdWidth": "half", "enabled": false},
                "place": {"order": 4, "sdWidth": "half", "enabled": true},
                "priority": {"order": 5, "sdWidth": "quarter", "enabled": true},
                "anpa_category": {"order": 7, "sdWidth": "full", "enabled": true},
                "subject_custom": {"order": 8, "sdWidth": "full", "enabled": true},
                "company_codes": {"order": 9, "sdWidth": "full", "enabled": false},
                "ednote": {"order": 10, "sdWidth": "full", "enabled": true},
                "headline": {"order": 11, "formatOptions": ["underline", "anchor", "bold", "removeFormat"], "enabled": true},
                "sms": {"order": 12, "enabled": false},
                "abstract": {"order": 13, "formatOptions": ["bold", "italic", "underline", "anchor", "removeFormat"], "enabled": true},
                "byline": {"order": 14, "enabled": true},
                "dateline": {"order": 15, "enabled": true},
                "body_html": {
                    "order": 16,
                    "formatOptions": ["h2", "bold", "italic", "underline", "quote", "anchor", "embed", "picture", "removeFormat"],
                    "enabled": true
                },
                "footer": {"order": 17, "enabled": false},
                "body_footer": {"order": 18, "enabled": false},
                "sign_off": {"order": 19, "enabled": true},
                "media": {"enabled": true},
                "media_description": {"enabled": true}
            }
        }
        """


    @auth
    Scenario: User can get profile with extended custom values
        Given "vocabularies"
        """
        [
          {
            "_id": "genre_custom",
            "display_name": "Genre",
            "type": "manageable",
            "service": {"all": 1},
            "single_value": true,
            "schema_field": "genre",
            "dependent": 1,
            "items": [
                {"is_active": true, "name": "Nyheter", "qcode": "Nyheter", "service": {"n": 1, "j": 1, "e": 1, "t": 1, "m": 1, "s": 1, "d": 1, "o": 1, "p": 1, "k": 1}},
                {"is_active": true, "name": "Faktaboks", "qcode": "Faktaboks", "service": {"n": 1}}
            ]
          },
          {
            "_id": "category",
            "display_name": "Category",
            "type": "manageable",
            "service": {"all": 1},
            "single_value": true,
            "dependent": 1,
            "items": [
                {"is_active": true, "name": "Innenriks", "qcode": "Innenriks", "service": {"n": 1, "s": 1, "e": 1, "t": 1, "m": 1, "j": 1, "i": 1}},
                {"is_active": true, "name": "Utenriks", "qcode": "Utenriks", "service": {"n": 1, "s": 1, "e": 1, "t": 1, "m": 1, "i": 1}}
            ]
          },
          {
            "_id": "subject_custom",
            "display_name": "Subject",
            "type": "manageable",
            "service": {"all": 1},
            "schema_field": "subject",
            "dependent": 0,
            "items": [
                {"is_active": true, "name": "Kultur og underholdning", "qcode": "01000000", "parent": null},
                {"is_active": true, "name": "Kriminalitet og rettsvesen", "qcode": "02000000", "parent": null}
            ]
          }
        ]
        """

        When we post to "content_types"
        """
        {
            "_id": "foo",
            "label": "Foo",
            "schema": {
                "slugline": {"maxlength": 24, "type": "string"}
            },
            "editor": {
                "slugline": {"order": 1, "sdWidth": "full", "enabled": true}
            }
        }
        """
        Then we get new resource
        """
        {
            "_id": "foo",
            "label": "Foo",
            "enabled": false,
            "created_by": "#CONTEXT_USER_ID#",
            "updated_by": "#CONTEXT_USER_ID#",
            "schema": {
                "slugline": {"maxlength": 24, "type": "string"}
            },
            "editor": {
                "slugline": {"order": 1, "sdWidth": "full", "enabled": true}
            }
        }
        """

        When we get "/content_types/#content_types._id#?edit=true"
        Then we get existing resource
        """
        {
            "_id": "foo",
            "label": "Foo",
            "enabled": false,
            "created_by": "#CONTEXT_USER_ID#",
            "updated_by": "#CONTEXT_USER_ID#",
            "schema": {
                "slugline": {"maxlength": 24, "type": "string"},
                "genre": {"type": "list"},
                "anpa_take_key": {},
                "place": {"type": "list"},
                "priority": {},
                "anpa_category": {"type": "list"},
                "subject": {
                  "type": "list",
                  "required": true,
                  "mandatory_in_list": {"scheme": {}},
                  "schema": {
                     "type": "dict",
                     "schema": {
                        "name": {},
                        "qcode": {},
                        "scheme": {
                           "type": "string",
                           "required": true,
                           "allowed": ["subject_custom", "category"]
                        },
                        "service": {"nullable": true},
                        "parent": {"nullable": true}
                      }
                  }
                },
                "company_codes": {"type": "list"},
                "ednote": {},
                "headline": {"maxlength": 64, "type": "string"},
                "sms": null,
                "abstract": {"maxlength": 160, "type": "string"},
                "byline": {"type": "string"},
                "dateline": {"type": "dict"},
                "body_html": {},
                "footer": null,
                "body_footer": null,
                "sign_off": {"type": "string"},
                "media": {},
                "media_description": {}
            },
            "editor": {
                "slugline": {"order": 1, "sdWidth": "full", "enabled": true},
                "genre_custom": {"order": 2, "sdWidth": "half", "enabled": false},
                "category": {"enabled": false},
                "anpa_take_key": {"order": 3, "sdWidth": "half", "enabled": false},
                "place": {"order": 4, "sdWidth": "half", "enabled": false},
                "priority": {"order": 5, "sdWidth": "quarter", "enabled": false},
                "anpa_category": {"order": 7, "sdWidth": "full", "enabled": false},
                "subject_custom": {"order": 8, "sdWidth": "full", "enabled": false},
                "company_codes": {"order": 9, "sdWidth": "full", "enabled": false},
                "ednote": {"order": 10, "sdWidth": "full", "enabled": false},
                "headline": {"order": 11, "formatOptions": ["underline", "anchor", "bold", "removeFormat"], "enabled": false},
                "sms": {"order": 12, "enabled": false},
                "abstract": {"order": 13, "formatOptions": ["bold", "italic", "underline", "anchor", "removeFormat"], "enabled": false},
                "byline": {"order": 14, "enabled": false},
                "dateline": {"order": 15, "enabled": false},
                "body_html": {
                    "order": 16,
                    "formatOptions": ["h2", "bold", "italic", "underline", "quote", "anchor", "embed", "picture", "removeFormat"],
                    "enabled": false
                },
                "footer": {"order": 17, "enabled": false},
                "body_footer": {"order": 18, "enabled": false},
                "sign_off": {"order": 19, "enabled": false},
                "media": {"enabled": false},
                "media_description": {"enabled": false}
            }
        }
        """

    @auth
    Scenario: Content profile defaults override user profile defaults
        Given "content_types"
        """
        [{"_id": "foo", "label": "Foo", "schema": {
            "byline": {"default": "By Foo"},
            "headline": null,
            "place": {"default": [{"name": "Prague"}]}
        }}]
        """
        When we patch "/users/#CONTEXT_USER_ID#"
        """
        {"byline": "By Admin"}
        """
        When we post to "/archive"
        """
        {"type": "text", "profile": "foo"}
        """
        Then we get new resource
        """
        {"byline": "By Foo", "place": [{"name": "Prague"}]}
        """

    @auth
    Scenario: Validate using content profile when publishing
        Given "content_types"
        """
        [{
            "_id": "foo",
            "schema" : {
                "body_html" : {
                    "required" : true,
                    "type" : "string"
                },
                "headline" : {
                    "required" : true,
                    "maxlength" : 42,
                    "type" : "string"
                },
                "body_footer" : {
                    "type" : "string",
                    "default" : "test",
                    "maxlength": null
                },
                "slugline" : {
                    "required" : true,
                    "maxlength" : 24,
                    "type" : "string"
                }
            }
        }]
        """

        And "desks"
        """
        [{"name": "sports"}]
        """

        When we post to "/archive"
        """
        {"type": "text", "profile": "foo", "task": {"desk": "#desks._id#"}}
        """

        When we patch "/archive/#archive._id#"
        """
        {"body_html": "body", "headline": "head", "slugline": "slug"}
        """

        And we publish "#archive._id#" with "publish" type and "published" state
        Then we get OK response
    
    @auth
    Scenario: Mark profile when used and prevent delete
        Given "content_types"
        """
        [{"_id": "foo"}, {"_id": "bar"}]
        """
        When we get "content_types/foo"
        Then we get existing resource
        """
        {"is_used": false}
        """
        When we post to "archive"
        """
        {"type": "text", "profile": "foo"}
        """
        And we get "content_types/foo"
        Then we get existing resource
        """
        {"is_used": true}
        """

        When we delete "content_types/foo"
        Then we get response code 202
        """
        {"is_used": true}
        """

        When we patch "archive/#archive._id#"
        """
        {"profile": "bar"}
        """
        And we delete "content_types/bar"
        Then we get response code 202

    @auth
    Scenario: When removing content profile keep associated templates
        Given "content_types"
        """
        [{"_id": "foo"}]
        """
        And "content_templates"
        """
        [{"template_name": "foo", "data": {"profile": "foo"}}, {"template_name": "bar"}]
        """
        When we get "content_templates/foo"
        Then we get response code 200

        When we delete "content_types/foo"
        And we get "content_templates/foo"
        Then we get response code 200
