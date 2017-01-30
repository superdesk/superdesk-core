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
            "editor": {
                "place": {
                    "sdWidth": "half",
                    "enabled": true,
                    "order": 4
                },
                "abstract": {
                    "formatOptions": ["bold", "italic", "underline", "anchor", "removeFormat"],
                    "enabled": true,
                    "order": 13
                },
                "slugline": {
                    "sdWidth": "full",
                    "enabled": true,
                    "order": 1
                },
                "headline": {
                    "formatOptions": ["underline", "anchor", "bold", "removeFormat"],
                    "enabled": true,
                    "order": 11
                },
                "body_footer": {
                    "enabled": false,
                    "order": 18
                },
                "sign_off": {
                    "enabled": true,
                    "order": 19
                },
                "footer": {
                    "enabled": false,
                    "order": 17
                },
                "anpa_category": {
                    "sdWidth": "full",
                    "enabled": true,
                    "order": 7
                },
                "dateline": {
                    "enabled": true,
                    "order": 15
                },
                "ednote": {
                    "sdWidth": "full",
                    "enabled": true,
                    "order": 10
                },
                "anpa_take_key": {
                    "sdWidth": "half",
                    "enabled": false,
                    "order": 3
                },
                "subject": {
                    "sdWidth": "full",
                    "enabled": true,
                    "order": 8
                },
                "genre": {
                    "sdWidth": "half",
                    "enabled": true,
                    "order": 2
                },
                "company_codes": {
                    "sdWidth": "full",
                    "enabled": false,
                    "order": 9
                },
                "priority": {
                    "sdWidth": "quarter",
                    "enabled": true,
                    "order": 5
                },
                "urgency": {
                    "sdWidth": "quarter",
                    "enabled": true,
                    "order": 6
                },
                "body_html": {
                    "formatOptions": ["h2", "bold", "italic", "underline", "quote", "anchor", "embed", "picture", "removeFormat"],
                    "enabled": true,
                    "order": 16
                },
                "byline": {
                    "enabled": true,
                    "order": 14
                },
                "media_description": {
                    "enabled": true
                },
                "sms": {
                    "enabled": false,
                    "order": 12
                },
                "feature_media": {
                    "enabled": false,
                    "order": 20
                }
            },
            "schema": {
                "abstract": {
                    "type": "string",
                    "required": false,
                    "maxlength": 160
                },
                "place": {
                    "type": "list",
                    "required": false
                },
                "slugline": {
                    "type": "string",
                    "required": false,
                    "maxlength": 24
                },
                "ednote": {
                    "type": "string",
                    "required": false
                },
                "sign_off": {
                    "type": "string",
                    "required": false
                },
                "byline": {
                    "type": "string",
                    "required": false
                },
                "body_html": {
                    "type": "string",
                    "required": false
                },
                "dateline": {
                    "type": "dict",
                    "required": false
                },
                "anpa_category": {
                    "type": "list",
                    "required": false
                },
                "anpa_take_key": {
                    "type": "string",
                    "required": false
                },
                "subject": {
                    "type": "list",
                    "schema": {},
                    "required": true,
                    "mandatory_in_list": {
                        "scheme": {}
                    }
                },
                "genre": {
                    "type": "list",
                    "required": false
                },
                "company_codes": {
                    "type": "list",
                    "required": false
                },
                "priority": {
                    "type": "integer",
                    "required": false
                },
                "urgency": {
                    "type": "integer",
                    "required": false
                },
                "headline": {
                    "type": "string",
                    "required": false,
                    "maxlength": 64
                },
                "media_description": {},
                "sms": {
                    "type": "string",
                    "required": false
                },
                "body_footer": {
                    "type": "string",
                    "required": false
                },
                "footer": {
                    "type": "string",
                    "required": false
                },
                "feature_media": {
                    "type": "picture",
                    "required": false
                }
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
                "ednote": {
                    "required": false,
                    "type": "string"
                },
                "priority": {
                    "type": "integer",
                    "required": false
                },
                "urgency": {
                    "type": "integer",
                    "required": false
                },
                "anpa_take_key": {
                    "required": false,
                    "type": "string"
                },
                "body_html": {
                    "required": false,
                    "type": "string"
                },
                "anpa_category": {
                    "type": "list",
                    "required": false
                },
                "subject": {
                    "mandatory_in_list": {
                        "scheme": {}
                    },
                    "type": "list",
                    "schema": {},
                    "required": true
                },
                "abstract": {
                    "maxlength": 160,
                    "required": false,
                    "type": "string"
                },
                "media_description": {},
                "headline": {
                    "maxlength": 64,
                    "required": false,
                    "type": "string"
                },
                "place": {
                    "type": "list",
                    "required": false
                },
                "byline": {
                    "required": false,
                    "type": "string"
                },
                "genre": {
                    "type": "list",
                    "required": false
                },
                "company_codes": {
                    "type": "list",
                    "required": false
                },
                "sign_off": {
                    "required": false,
                    "type": "string"
                },
                "slugline": {
                    "maxlength": 24,
                    "type": "string"
                },
                "dateline": {
                    "type": "dict",
                    "required": false
                },
                "sms": {
                    "required": false,
                    "type": "string"
                },
                "body_footer": {
                    "type": "string",
                    "required": false
                },
                "footer": {
                    "type": "string",
                    "required": false
                },
                "feature_media": {
                    "type": "picture",
                    "required": false
                }
            },
            "editor": {
                "ednote": {
                    "enabled": false,
                    "order": 10,
                    "sdWidth": "full"
                },
                "priority": {
                    "enabled": false,
                    "order": 5,
                    "sdWidth": "quarter"
                },
                "urgency": {
                    "enabled": false,
                    "order": 6,
                    "sdWidth": "quarter"
                },
                "anpa_take_key": {
                    "enabled": false,
                    "order": 3,
                    "sdWidth": "half"
                },
                "body_html": {
                    "enabled": false,
                    "order": 16,
                    "formatOptions": ["h2", "bold", "italic", "underline", "quote", "anchor", "embed", "picture", "removeFormat"]
                },
                "anpa_category": {
                    "enabled": false,
                    "order": 7,
                    "sdWidth": "full"
                },
                "subject": {
                    "enabled": false,
                    "order": 8,
                    "sdWidth": "full"
                },
                "abstract": {
                    "enabled": false,
                    "order": 13,
                    "formatOptions": ["bold", "italic", "underline", "anchor", "removeFormat"]
                },
                "media_description": {
                    "enabled": false
                },
                "headline": {
                    "enabled": false,
                    "order": 11,
                    "formatOptions": ["underline", "anchor", "bold", "removeFormat"]
                },
                "place": {
                    "enabled": false,
                    "order": 4,
                    "sdWidth": "half"
                },
                "byline": {
                    "enabled": false,
                    "order": 14
                },
                "sms": {
                    "enabled": false,
                    "order": 12
                },
                "footer": {
                    "enabled": false,
                    "order": 17
                },
                "body_footer": {
                    "enabled": false,
                    "order": 18
                },
                "genre": {
                    "enabled": false,
                    "order": 2,
                    "sdWidth": "half"
                },
                "company_codes": {
                    "enabled": false,
                    "order": 9,
                    "sdWidth": "full"
                },
                "sign_off": {
                    "enabled": false,
                    "order": 19
                },
                "slugline": {
                    "enabled": true,
                    "order": 1,
                    "sdWidth": "full"
                },
                "dateline": {
                    "enabled": false,
                    "order": 15
                },
                "feature_media": {
                    "enabled": false,
                    "order": 20
                }
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
                "dateline": {
                    "type": "dict",
                    "required": false
                },
                "media_description": {},
                "priority": {
                    "type": "integer",
                    "required": false
                },
                "urgency": {
                    "type": "integer",
                    "required": false
                },
                "subject_custom": {
                    "mandatory_in_list": {
                        "scheme": {}
                    },
                    "type": "list",
                    "required": true,
                    "schema": {}
                },
                "ednote": {
                    "type": "string",
                    "required": false
                },
                "abstract": {
                    "type": "string",
                    "maxlength": 160,
                    "required": false
                },
                "place": {
                    "type": "list",
                    "required": false
                },
                "sign_off": {
                    "type": "string",
                    "required": false
                },
                "genre_custom": {
                    "type": "list",
                    "required": false
                },
                "anpa_take_key": {
                    "type": "string",
                    "required": false
                },
                "slugline": {
                    "type": "string",
                    "maxlength": 24,
                    "required": false
                },
                "category": {
                    "type": "list",
                    "required": false
                },
                "byline": {
                    "type": "string",
                    "required": false
                },
                "body_html": {
                    "type": "string",
                    "required": false
                },
                "company_codes": {
                    "type": "list",
                    "required": false
                },
                "anpa_category": {
                    "type": "list",
                    "required": false
                },
                "headline": {
                    "type": "string",
                    "maxlength": 64,
                    "required": false
                },
                "sms": {
                    "type": "string",
                    "required": false
                },
                "body_footer": {
                    "type": "string",
                    "required": false
                },
                "footer": {
                    "type": "string",
                    "required": false
                },
                "feature_media": {
                    "type": "picture",
                    "required": false
                }
            },
            "editor": {
                "dateline": {
                    "order": 15,
                    "enabled": true
                },
                "media_description": {
                    "enabled": true
                },
                "priority": {
                    "order": 5,
                    "sdWidth": "quarter",
                    "enabled": true
                },
                "urgency": {
                    "order": 6,
                    "sdWidth": "quarter",
                    "enabled": true
                },
                "subject_custom": {
                    "field_name": "subject",
                    "order": 8,
                    "sdWidth": "full",
                    "enabled": true
                },
                "anpa_take_key": {
                    "order": 3,
                    "sdWidth": "half",
                    "enabled": false
                },
                "abstract": {
                    "order": 13,
                    "enabled": true,
                    "formatOptions": ["bold", "italic", "underline", "anchor", "removeFormat"]
                },
                "place": {
                    "order": 4,
                    "sdWidth": "half",
                    "enabled": true
                },
                "sign_off": {
                    "order": 19,
                    "enabled": true
                },
                "body_footer": {
                    "order": 18,
                    "enabled": false
                },
                "genre_custom": {
                    "field_name": "genre",
                    "order": 2,
                    "sdWidth": "half",
                    "enabled": true
                },
                "ednote": {
                    "order": 10,
                    "sdWidth": "full",
                    "enabled": true
                },
                "slugline": {
                    "order": 1,
                    "sdWidth": "full",
                    "enabled": true
                },
                "category": {
                    "field_name": "category",
                    "enabled": false
                },
                "byline": {
                    "order": 14,
                    "enabled": true
                },
                "body_html": {
                    "order": 16,
                    "enabled": true,
                    "formatOptions": ["h2", "bold", "italic", "underline", "quote", "anchor", "embed", "picture", "removeFormat"]
                },
                "footer": {
                    "order": 17,
                    "enabled": false
                },
                "company_codes": {
                    "order": 9,
                    "sdWidth": "full",
                    "enabled": false
                },
                "sms": {
                    "order": 12,
                    "enabled": false
                },
                "anpa_category": {
                    "order": 7,
                    "sdWidth": "full",
                    "enabled": true
                },
                "headline": {
                    "order": 11,
                    "enabled": true,
                    "formatOptions": ["underline", "anchor", "bold", "removeFormat"]
                },
                "feature_media": {
                    "enabled": false,
                    "order": 20
                }
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
            "editor": {
                "footer": {
                    "order": 17,
                    "enabled": false
                },
                "body_footer": {
                    "order": 18,
                    "enabled": false
                },
                "ednote": {
                    "sdWidth": "full",
                    "order": 10,
                    "enabled": false
                },
                "media_description": {
                    "enabled": false
                },
                "body_html": {
                    "formatOptions": ["h2", "bold", "italic", "underline", "quote", "anchor", "embed", "picture", "removeFormat"],
                    "enabled": false,
                    "order": 16
                },
                "dateline": {
                    "order": 15,
                    "enabled": false
                },
                "anpa_category": {
                    "sdWidth": "full",
                    "order": 7,
                    "enabled": false
                },
                "category": {
                    "field_name": "category",
                    "enabled": false
                },
                "place": {
                    "sdWidth": "half",
                    "order": 4,
                    "enabled": false
                },
                "sign_off": {
                    "order": 19,
                    "enabled": false
                },
                "slugline": {
                    "sdWidth": "full",
                    "order": 1,
                    "enabled": true
                },
                "headline": {
                    "formatOptions": ["underline", "anchor", "bold", "removeFormat"],
                    "enabled": false,
                    "order": 11
                },
                "subject_custom": {
                    "sdWidth": "full",
                    "field_name": "subject",
                    "order": 8,
                    "enabled": false
                },
                "sms": {
                    "order": 12,
                    "enabled": false
                },
                "abstract": {
                    "formatOptions": ["bold", "italic", "underline", "anchor", "removeFormat"],
                    "enabled": false,
                    "order": 13
                },
                "company_codes": {
                    "sdWidth": "full",
                    "order": 9,
                    "enabled": false
                },
                "priority": {
                    "sdWidth": "quarter",
                    "order": 5,
                    "enabled": false
                },
                "urgency": {
                    "sdWidth": "quarter",
                    "order": 6,
                    "enabled": false
                },
                "anpa_take_key": {
                    "sdWidth": "half",
                    "order": 3,
                    "enabled": false
                },
                "genre_custom": {
                    "sdWidth": "half",
                    "field_name": "genre",
                    "order": 2,
                    "enabled": false
                },
                "byline": {
                    "order": 14,
                    "enabled": false
                },
                "feature_media": {
                    "enabled": false,
                    "order": 20
                }
            },
            "schema": {
                "ednote": {
                    "type": "string",
                    "required": false
                },
                "media_description": {},
                "body_html": {
                    "type": "string",
                    "required": false
                },
                "dateline": {
                    "type": "dict",
                    "required": false
                },
                "anpa_category": {
                    "type": "list",
                    "required": false
                },
                "category": {
                    "type": "list",
                    "required": false
                },
                "place": {
                    "type": "list",
                    "required": false
                },
                "sign_off": {
                    "type": "string",
                    "required": false
                },
                "slugline": {
                    "type": "string",
                    "maxlength": 24
                },
                "headline": {
                    "type": "string",
                    "maxlength": 64,
                    "required": false
                },
                "subject_custom": {
                    "type": "list",
                    "mandatory_in_list": {
                        "scheme": {}
                    },
                    "schema": {},
                    "required": true
                },
                "abstract": {
                    "type": "string",
                    "maxlength": 160,
                    "required": false
                },
                "company_codes": {
                    "type": "list",
                    "required": false
                },
                "priority": {
                    "type": "integer",
                    "required": false
                },
                "urgency": {
                    "type": "integer",
                    "required": false
                },
                "anpa_take_key": {
                    "type": "string",
                    "required": false
                },
                "genre_custom": {
                    "type": "list",
                    "required": false
                },
                "byline": {
                    "type": "string",
                    "required": false
                },
                "sms": {
                    "type": "string",
                    "required": false
                },
                "body_footer": {
                    "type": "string",
                    "required": false
                },
                "footer": {
                    "type": "string",
                    "required": false
                },
                "feature_media": {
                    "type": "picture",
                    "required": false
                }
            }
        }
        """

   @auth
    Scenario: User can add profile with custom subject disabled and category(saved on subject) enabled
        Given "vocabularies"
        """
        [
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
            "enabled": false,
            "created_by": "#CONTEXT_USER_ID#",
            "updated_by": "#CONTEXT_USER_ID#",
            "schema": {
                "subject": {
                    "schema": {
                        "schema": {
                            "scheme": {
                                "allowed": ["category"],
                                "required": true,
                                "type": "string"
                            }
                        },
                        "type": "dict"
                    },
                    "type": "list",
                    "required": true,
                    "mandatory_in_list": {"scheme": {"category": "category"}}
                }
            },
            "editor": {
                "category": {
                    "field_name": "category",
                    "enabled": true
                }
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
            "updated_by": "#CONTEXT_USER_ID#"
        }
        """

        When we patch "/content_types/#content_types._id#"
        """
        {
            "schema": {
                "subject_custom": {
                    "type": "list",
                    "mandatory_in_list": {
                        "scheme": {}
                    },
                    "schema": {},
                    "required": true
                },
                "category": {
                    "type": "list",
                    "required": false
                }
            },
            "editor": {
                "category": {
                    "field_name": "category",
                    "enabled": true
                },
                "subject_custom": {
                    "sdWidth": "full",
                    "field_name": "subject",
                    "order": 8,
                    "enabled": false
                }
            }
        }
        """

        When we get "/content_types/#content_types._id#"
        Then we get existing resource
        """
        {
            "_id": "foo",
            "label": "Foo",
            "enabled": false,
            "created_by": "#CONTEXT_USER_ID#",
            "updated_by": "#CONTEXT_USER_ID#",
            "schema": {
                "subject": {
                    "schema": {
                        "schema": {
                            "scheme": {
                                "allowed": ["category"],
                                "required": true,
                                "type": "string"
                            }
                        },
                        "type": "dict"
                    },
                    "type": "list",
                    "required": false,
                    "mandatory_in_list": {"scheme": {}}
                }
            },
            "editor": {
                "category": {
                    "field_name": "category",
                    "enabled": true
                }
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