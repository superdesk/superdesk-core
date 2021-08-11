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
                    "order": 7
                },
                "abstract": {
                    "formatOptions": ["bold", "italic", "underline", "link"],
                    "enabled": true,
                    "order": 17
                },
                "feature_media": {
                    "enabled": true
                },
                "slugline": {
                    "sdWidth": "full",
                    "enabled": true,
                    "order": 1
                },
                "keywords": {
                    "sdWidth": "full",
                    "enabled": false,
                    "order": 2
                },
                "language": {
                    "sdWidth": "half",
                    "enabled": false,
                    "order": 3
                },
                "headline": {
                    "formatOptions": [],
                    "enabled": true,
                    "order": 15
                },
                "body_footer": {
                    "enabled": false,
                    "order": 22
                },
                "sign_off": {
                    "enabled": true,
                    "order": 23
                },
                "footer": {
                    "enabled": false,
                    "order": 21
                },
                "anpa_category": {
                    "sdWidth": "full",
                    "enabled": true,
                    "order": 10
                },
                "dateline": {
                    "enabled": true,
                    "order": 19
                },
                "ednote": {
                    "sdWidth": "full",
                    "enabled": true,
                    "order": 13
                },
                "authors": {
                    "sdWidth": "full",
                    "enabled": true,
                    "order": 14
                },
                "anpa_take_key": {
                    "sdWidth": "half",
                    "enabled": false,
                    "order": 6
                },
                "subject": {
                    "sdWidth": "full",
                    "enabled": true,
                    "order": 11
                },
                "genre": {
                    "sdWidth": "half",
                    "enabled": true,
                    "order": 5
                },
                "company_codes": {
                    "sdWidth": "full",
                    "enabled": false,
                    "order": 12
                },
                "priority": {
                    "sdWidth": "quarter",
                    "enabled": true,
                    "order": 8
                },
                "urgency": {
                    "sdWidth": "quarter",
                    "enabled": true,
                    "order": 9
                },
                "body_html": {
                    "formatOptions": ["h2", "bold", "italic", "underline", "quote", "link", "embed", "media"],
                    "enabled": true,
                    "order": 20
                },
                "byline": {
                    "enabled": true,
                    "order": 18
                },
                "media_description": {
                    "enabled": true
                },
                "sms": {
                    "enabled": false,
                    "order": 16
                },
                "usageterms": {
                	"order": 4,
                	"enabled": false,
                	"sdWidth": "full"
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
                "feature_media": {},
                "slugline": {
                    "type": "string",
                    "required": false,
                    "maxlength": 24
                },
                "ednote": {
                    "type": "string",
                    "required": false
                },
                "authors": {
                    "required": false,
                    "schema": {
                        "schema": {
                            "name": {
                                "type": "string"
                            },
                            "parent": {
                                "type": "string"
                            },
                            "role": {
                                "type": "string"
                            }
                        },
                        "type": "dict"
                    },
                    "type": "list"
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
                }
            }
        }
        """

        When we patch "/content_types/#content_types._id#"
        """
        {"schema": {"headline": {
            "required": false,
            "minlength": 5
        }}}
        """

        And we get "/content_types/#content_types._id#"
        Then we get existing resource
        """
        {"schema": {"headline": {"minlength": 5}}}
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
                "authors": {
                    "required": false,
                    "schema": {
                        "schema": {
                            "name": {
                                "type": "string"
                            },
                            "parent": {
                                "type": "string"
                            },
                            "role": {
                                "type": "string"
                            }
                        },
                        "type": "dict"
                    },
                    "type": "list"
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
                "feature_media": {},
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
                }
            },
            "editor": {
                "ednote": {
                    "enabled": false,
                    "order": 13,
                    "sdWidth": "full"
                },
                "authors": {
                    "enabled": false,
                    "sdWidth": "full",
                    "order": 14
                },
                "priority": {
                    "enabled": false,
                    "order": 8,
                    "sdWidth": "quarter"
                },
                "urgency": {
                    "enabled": false,
                    "order": 9,
                    "sdWidth": "quarter"
                },
                "anpa_take_key": {
                    "enabled": false,
                    "order": 6,
                    "sdWidth": "half"
                },
                "body_html": {
                    "enabled": false,
                    "order": 20,
                    "formatOptions": ["h2", "bold", "italic", "underline", "quote", "link", "embed", "media"]
                },
                "anpa_category": {
                    "enabled": false,
                    "order": 10,
                    "sdWidth": "full"
                },
                "feature_media": {
                    "enabled": false
                },
                "subject": {
                    "enabled": false,
                    "order": 11,
                    "sdWidth": "full"
                },
                "abstract": {
                    "enabled": false,
                    "order": 17,
                    "formatOptions": ["bold", "italic", "underline", "link"]
                },
                "media_description": {
                    "enabled": false
                },
                "headline": {
                    "enabled": false,
                    "order": 15,
                    "formatOptions": []
                },
                "place": {
                    "enabled": false,
                    "order": 7,
                    "sdWidth": "half"
                },
                "byline": {
                    "enabled": false,
                    "order": 18
                },
                "sms": {
                    "enabled": false,
                    "order": 16
                },
                "footer": {
                    "enabled": false,
                    "order": 21
                },
                "body_footer": {
                    "enabled": false,
                    "order": 22
                },
                "genre": {
                    "enabled": false,
                    "order": 5,
                    "sdWidth": "half"
                },
                "company_codes": {
                    "enabled": false,
                    "order": 12,
                    "sdWidth": "full"
                },
                "sign_off": {
                    "enabled": false,
                    "order": 23
                },
                "slugline": {
                    "enabled": true,
                    "order": 1,
                    "sdWidth": "full"
                },
                "keywords": {
                    "enabled": false,
                    "order": 2,
                    "sdWidth": "full"
                },
                "language": {
                    "enabled": false,
                    "order": 3,
                    "sdWidth": "half"
                },
                "dateline": {
                    "enabled": false,
                    "order": 19
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
            "display_name": "NTB Category",
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
                "authors": {
                    "required": false,
                    "schema": {
                        "schema": {
                            "name": {
                                "type": "string"
                            },
                            "parent": {
                                "type": "string"
                            },
                            "role": {
                                "type": "string"
                            }
                        },
                        "type": "dict"
                    },
                    "type": "list"
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
                "feature_media": {},
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
                }
            },
            "editor": {
                "dateline": {
                    "order": 19,
                    "enabled": true
                },
                "media_description": {
                    "enabled": true
                },
                "priority": {
                    "order": 8,
                    "sdWidth": "quarter",
                    "enabled": true
                },
                "urgency": {
                    "order": 9,
                    "sdWidth": "quarter",
                    "enabled": true
                },
                "subject_custom": {
                    "field_name": "Subject",
                    "order": 11,
                    "sdWidth": "full",
                    "enabled": true
                },
                "anpa_take_key": {
                    "order": 6,
                    "sdWidth": "half",
                    "enabled": false
                },
                "abstract": {
                    "order": 17,
                    "enabled": true,
                    "formatOptions": ["bold", "italic", "underline", "link"]
                },
                "place": {
                    "order": 7,
                    "sdWidth": "half",
                    "enabled": true
                },
                "sign_off": {
                    "order": 23,
                    "enabled": true
                },
                "body_footer": {
                    "order": 22,
                    "enabled": false
                },
                "genre_custom": {
                    "field_name": "Genre",
                    "order": 5,
                    "sdWidth": "half",
                    "enabled": true
                },
                "ednote": {
                    "order": 13,
                    "sdWidth": "full",
                    "enabled": true
                },
                "authors": {
                    "sdWidth": "full",
                    "enabled": true,
                    "order": 14
                },
                "slugline": {
                    "order": 1,
                    "sdWidth": "full",
                    "enabled": true
                },
                "keywords": {
                    "order": 2,
                    "sdWidth": "full",
                    "enabled": false
                },
                "category": {
                    "field_name": "NTB Category",
                    "enabled": false
                },
                "byline": {
                    "order": 18,
                    "enabled": true
                },
                "body_html": {
                    "order": 20,
                    "enabled": true,
                    "formatOptions": ["h2", "bold", "italic", "underline", "quote", "link", "embed", "media"]
                },
                "footer": {
                    "order": 21,
                    "enabled": false
                },
                "company_codes": {
                    "order": 12,
                    "sdWidth": "full",
                    "enabled": false
                },
                "feature_media": {
                    "enabled": true
                },
                "sms": {
                    "order": 16,
                    "enabled": false
                },
                "anpa_category": {
                    "order": 10,
                    "sdWidth": "full",
                    "enabled": true
                },
                "headline": {
                    "order": 15,
                    "enabled": true,
                    "formatOptions": []
                },
                "usageterms": {
                	"order": 4,
                	"enabled": false,
                	"sdWidth": "full"
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
            "display_name": "NTB Category",
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
                    "order": 21,
                    "enabled": false
                },
                "body_footer": {
                    "order": 22,
                    "enabled": false
                },
                "ednote": {
                    "sdWidth": "full",
                    "order": 13,
                    "enabled": false
                },
                "authors": {
                    "sdWidth": "full",
                    "enabled": false,
                    "order": 14
                },
                "media_description": {
                    "enabled": false
                },
                "body_html": {
                    "formatOptions": ["h2", "bold", "italic", "underline", "quote", "link", "embed", "media"],
                    "enabled": false,
                    "order": 20
                },
                "dateline": {
                    "order": 19,
                    "enabled": false
                },
                "feature_media": {
                    "enabled": false
                },
                "anpa_category": {
                    "sdWidth": "full",
                    "order": 10,
                    "enabled": false
                },
                "category": {
                    "field_name": "NTB Category",
                    "enabled": false
                },
                "place": {
                    "sdWidth": "half",
                    "order": 7,
                    "enabled": false
                },
                "sign_off": {
                    "order": 23,
                    "enabled": false
                },
                "slugline": {
                    "sdWidth": "full",
                    "order": 1,
                    "enabled": true
                },
                "keywords": {
                    "sdWidth": "full",
                    "order": 2,
                    "enabled": false
                },
                "language": {
                    "sdWidth": "half",
                    "order": 3,
                    "enabled": false
                },
                "headline": {
                    "formatOptions": [],
                    "enabled": false,
                    "order": 15
                },
                "subject_custom": {
                    "sdWidth": "full",
                    "field_name": "Subject",
                    "order": 11,
                    "enabled": false
                },
                "sms": {
                    "order": 16,
                    "enabled": false
                },
                "abstract": {
                    "formatOptions": ["bold", "italic", "underline", "link"],
                    "enabled": false,
                    "order": 17
                },
                "company_codes": {
                    "sdWidth": "full",
                    "order": 12,
                    "enabled": false
                },
                "priority": {
                    "sdWidth": "quarter",
                    "order": 8,
                    "enabled": false
                },
                "urgency": {
                    "sdWidth": "quarter",
                    "order": 9,
                    "enabled": false
                },
                "anpa_take_key": {
                    "sdWidth": "half",
                    "order": 6,
                    "enabled": false
                },
                "genre_custom": {
                    "sdWidth": "half",
                    "field_name": "Genre",
                    "order": 5,
                    "enabled": false
                },
                "byline": {
                    "order": 18,
                    "enabled": false
                },
                "usageterms": {
                	"order": 4,
                	"enabled": false,
                	"sdWidth": "full"
                }
            },
            "schema": {
                "ednote": {
                    "type": "string",
                    "required": false
                },
                "authors": {
                    "required": false,
                    "schema": {
                        "schema": {
                            "name": {
                                "type": "string"
                            },
                            "parent": {
                                "type": "string"
                            },
                            "role": {
                                "type": "string"
                            }
                        },
                        "type": "dict"
                    },
                    "type": "list"
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
                "feature_media": {},
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
            "display_name": "NTB Category",
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
                "genre": {
                    "type": "list",
                    "required": false,
                    "nullable": true
                },
                "subject": {
                    "schema": {
                        "schema": {
                            "scheme": {
                                "allowed": ["category"],
                                "required": true,
                                "type": "string",
                                "nullable": true
                            }
                        },
                        "type": "dict"
                    },
                    "type": "list",
                    "required": true,
                    "mandatory_in_list": {"scheme": {"category": {"required": true}}}
                }
            },
            "editor": {
                "genre_custom": {
                    "sdWidth": "half",
                    "order": 5,
                    "enabled": true
                },
                "category": {
                    "field_name": "NTB Category",
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
                "genre_custom": {
                    "type": "list",
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
                "category": {
                    "type": "list",
                    "required": false,
                    "default" : [
                        {
                            "scheme" : "category",
                            "qcode" : "Innenriks",
                            "name" : "Innenriks",
                            "service" : {
                                "t" : 1,
                                "e" : 1,
                                "j" : 1,
                                "s" : 1,
                                "n" : 1,
                                "m" : 1,
                                "i" : 1
                            }
                        }
                    ]
                }
            },
            "editor": {
                "category": {
                    "field_name": "NTB Category",
                    "enabled": true
                },
                "genre_custom": {
                    "field_name": "Genre",
                    "enabled": true
                },
                "subject_custom": {
                    "sdWidth": "full",
                    "field_name": "Subject",
                    "order": 11,
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
                "genre": {
                    "type": "list",
                    "required": false,
                    "nullable": true
                },
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
                    "mandatory_in_list": {"scheme": {}},
                    "default" : [
                        {
                            "scheme" : "category",
                            "qcode" : "Innenriks",
                            "name" : "Innenriks",
                            "service" : {
                                "t" : 1,
                                "e" : 1,
                                "j" : 1,
                                "s" : 1,
                                "n" : 1,
                                "m" : 1,
                                "i" : 1
                            }
                        }
                    ]
                }
            },
            "editor": {
                "category": {
                    "field_name": "NTB Category",
                    "enabled": true
                },
                "genre_custom": {
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
        Given "vocabularies"
        """
        [{"_id": "foo", "field_type": "text"}]
        """
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
                },
                "foo": {
                    "required": true,
                    "maxlength": 20
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
        {"body_html": "body", "headline": "head", "slugline": "slug", "extra": {"foo": "<b>test</b>"}}
        """

        And we publish "#archive._id#" with "publish" type and "published" state
        Then we get OK response

        When we get "/published/#archive._id#"
        Then we get existing resource
        """
        {"extra": {"foo": "<b>test</b>"}}
        """

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

    @auth
    Scenario: Disabling content profile fails if there are references
        Given "content_types"
        """
        [{"_id": "foo", "enabled": true}]
        """
        And "content_templates"
        """
        [{"template_name": "foo", "data": {"profile": "foo"}}, {"template_name": "bar"}]
        """
        When we get "content_templates/foo"
        Then we get response code 200
        When we patch "content_types/foo"
        """
        {"enabled": false}
        """
        Then we get response code 400
        When we patch "content_templates/foo"
        """
        {"data": {"profile": null}}
        """
        When we patch "content_types/#content_types._id#"
        """
        {"enabled": false}
        """
        Then we get response code 200
        When we patch "content_types/#content_types._id#"
        """
        {"enabled": true}
        """
        When we post to "/desks"
        """
        {"name": "Sports Desk", "default_content_profile": "foo"}
        """
        When we patch "content_types/#content_types._id#"
        """
        {"enabled": false}
        """
        Then we get response code 400

    @auth
    Scenario: Updated content profile removes the field value from template
        Given "content_types"
        """
        [{"_id": "foo", "label": "Foo", "schema": {
            "headline": {
                "maxlength" : 64,
                "type" : "string",
                "required" : false,
                "nullable" : true
            },
            "slugline" : {
                "type" : "string",
                "nullable" : true,
                "maxlength" : 24,
                "required" : false
            },
            "place": {"default": [{"name": "Prague"}]}
        }}]
        """
        And "content_templates"
        """
        [{
            "template_name": "foo",
            "data": {
                "slugline": "Testing the slugline",
                "headline": "Testing the headline",
                "profile": "foo"
            }
        }]
        """
        When we patch "content_types/foo"
        """
        {"schema": {
            "headline": null,
            "slugline" : {
                "type" : "string",
                "nullable" : true,
                "maxlength" : 24,
                "required" : false
            },
            "place": {"default": [{"name": "Prague"}]}
        }}
        """
        Then we get updated response
        """
        {"updated_by": "#CONTEXT_USER_ID#"}
        """
        When we get "content_templates"
        Then we get list with 1 items
        """
        {"_items": [{
            "template_name": "foo",
            "data": {
                "slugline": "Testing the slugline",
                "profile": "foo"
            }
          }]
        }
        """
        And there is no "headline" in data

    @auth
    Scenario: Add custom fields on edit
        Given "vocabularies"
        """
        [
            {"_id": "foo", "display_name": "Foo", "field_type": "text"},
            {"_id": "bar", "display_name": "Bar", "service": {"all": 1}}
        ]
        """
        And "content_types"
        """
        [{"_id": "profile"}]
        """
        When we get "/content_types/profile?edit=true"
        Then we get existing resource
        """
        {
            "schema": {
                "foo": {
                    "type": "text",
                    "required": false
                }
            },
            "editor": {
                "foo": {
                    "enabled": false,
                    "field_name": "Foo"
                }
            }
        }
        """
        When we patch "/content_types/profile"
        """
        {
            "editor": {"foo": {"enabled": true}},
            "schema": {"foo": {"required": true, "type": "text"}}
        }
        """
        And we get "/content_types/profile?edit=true"
        Then we get existing resource
        """
        {
            "editor": {"foo": {"enabled": true}}
        }
        """

    @auth
    Scenario: Remove custom vocabulary when used in a content type
        Given "vocabularies"
        """
        [
            {"_id": "foo", "display_name": "Foo", "field_type": "text", "items": []}
        ]
        """
        And "content_types"
        """
        [{"_id": "profile",
          "label": "Profile",
          "editor": {"foo": {"enabled": true}},
          "schema": {"foo": {"required": true, "type": "text"}}
        }]
        """
		When we delete "/vocabularies/foo"
	    Then we get error 400
	    """
	    {"_message": "Vocabulary Foo is used in 1 content type(s)",
	     "_status": "ERR",
	     "_issues": {
	     	"content_types": [{
	     		"_id": "profile",
	     		"label": "Profile",
	     		"_links": {
	     			"self": {"href": "__any_value__"}
	     		}
	     	}]
	     }
	    }
	    """

    @auth
    Scenario: Keep user preffered required status for core subjects
        Given "vocabularies"
        """
        [
            {"_id": "foo", "service": {"all": 1}, "field_type": null}
        ]
        """
        When we post to "content_types"
        """
        {"_id": "test"}
        """
        And we patch "content_types/test"
        """
        {"schema": {
            "foo": {
                "default": [],
                "required": false,
                "type": "list"
            },
            "subject": {
                "required": false,
                "default": [],
                "nullable": true,
                "schema": {},
                "type": "list",
                "mandatory_in_list": {
                    "scheme": {}
                }
            }
        }, "editor": {
            "foo": {
                "enabled": true,
                "required": false
            },
            "subject": {
                "enabled": true,
                "required": false
            }
        }}
        """
        And we patch "content_types/test"
        """
        {"schema": {
            "foo": {
                "default": [],
                "required": false,
                "type": "list"
            },
            "subject": {
                "required": true,
                "default": [],
                "nullable": true,
                "schema": {},
                "type": "list",
                "mandatory_in_list": {
                    "scheme": {}
                }
            }
        }}
        """

        When we get "content_types/test"
        Then we get existing resource
        """
        {"schema": {"subject": {"required": true}}}
        """

        When we patch "content_types/test"
        """
        {"schema": {
            "foo": {
                "default": [],
                "required": true,
                "type": "list"
            },
            "subject": {
                "required": false,
                "default": [],
                "nullable": true,
                "schema": {},
                "type": "list",
                "mandatory_in_list": {
                    "scheme": {}
                }
            }
        }}
        """

        When we get "content_types/test"
        Then we get existing resource
        """
        {"schema": {"subject": {"required": false}}}
        """

    @auth
    Scenario: Only 1 profile can be added for non text item types
        When we post to "content_types"
        """
        {"_id": "foo", "item_type": "picture"}
        """
        Then we get new resource
        When we post to "content_types"
        """
        {"_id": "bar", "item_type": "picture"}
        """
        Then we get error 400
        """
        {"_status": "ERR", "_issues": {"item_type": "Only 1 instance is allowed."}}
        """

    @auth
    Scenario: Updating the content profile doesn't change template metadata
        Given "content_types"
        """
        [{"_id": "foo", "label": "Foo", "schema": {
            "headline": {
                "maxlength" : 64,
                "type" : "string",
                "required" : false,
                "nullable" : true
            },
            "slugline" : {
                "type" : "string",
                "nullable" : true,
                "maxlength" : 24,
                "required" : false
            },
            "place": {"default": [{"name": "Prague"}]}
        }}]
        """
        And "content_templates"
        """
        [{
            "template_name": "foo",
            "data": {
                "slugline": "Testing the slugline",
                "headline": "Testing the headline",
                "profile": "foo",
                "language": "fr"
            }
        }]
        """
        When we patch "content_types/foo"
        """
        {"schema": {
            "headline": null,
            "slugline" : {
                "type" : "string",
                "nullable" : true,
                "maxlength" : 24,
                "required" : false
            },
            "language": null,
            "place": {"default": [{"name": "Prague"}]}
        }}
        """
        Then we get updated response
        """
        {"updated_by": "#CONTEXT_USER_ID#"}
        """
        When we get "content_templates"
        Then we get list with 1 items
        """
        {"_items": [{
            "template_name": "foo",
            "data": {
                "slugline": "Testing the slugline",
                "profile": "foo",
                "language": "fr"
            }
          }]
        }
        """
        And there is no "headline" in data

    @auth
    Scenario: Removing the keywords field from content profile should not show the keywords field again 
        Given "vocabularies"
        """
        [
            {
                "_id": "keywords", 
                "display_name": "keywords_little", 
                "service": {"all": 1},
                "items": [{"name": "k1", "parent": "k1", "qcode": "k1"}]
            }
        ]
        """
        And "content_types"
        """
        [{"_id": "profile"}]
        """
        When we get "/content_types/profile?edit=true"
        Then we get existing resource
        """
        {
            "schema": {
                "keywords": {
                    "type": "list",
                    "required": false
                }
            },
            "editor": {
                "keywords": {
                    "enabled": false,
                    "field_name": "keywords_little"
                }
            }
        }
        """
        When we patch "/content_types/profile"
        """
        {
            "editor": {"keywords": {"enabled": true}}
        }
        """
        And we get "/content_types/profile?edit=true"
        Then we get existing resource
        """
        {
            "editor": {"keywords": {"enabled": true}}
        }
        """
         When we patch "/content_types/profile"
        """
        {
            "editor": {"keywords": {"enabled": false}}
        }
        """
        And we get "/content_types/profile?edit=true"
        Then we get existing resource
        """
        {
            "editor": {"keywords": {"enabled": false}}
        }
        """
