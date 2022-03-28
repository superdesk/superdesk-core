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
                "headline": {
                    "formatOptions": [],
                    "enabled": true,
                    "order": 15
                }
            },
            "schema": {
                "headline": {
                    "type": "string",
                    "required": true,
                    "maxlength": 64
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
                "slugline": {
                    "maxlength": 24,
                    "type": "string"
                }
            },
            "editor": {
                "ednote": {
                    "enabled": false,
                    "order": 13,
                    "sdWidth": "full"
                },
                "slugline": {
                    "enabled": true,
                    "order": 1,
                    "sdWidth": "full"
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
                "subject_custom": {
                    "mandatory_in_list": {
                        "scheme": {}
                    },
                    "type": "list",
                    "required": false,
                    "schema": {}
                }
            },
            "editor": {
                "subject_custom": {
                    "field_name": "Subject",
                    "order": 11,
                    "sdWidth": "full",
                    "enabled": true
                },
                "genre_custom": {
                    "field_name": "Genre",
                    "order": 5,
                    "sdWidth": "half",
                    "enabled": true
                },
                "category": {
                    "field_name": "NTB Category",
                    "enabled": false
                },
                "anpa_category": {
                    "order": 10,
                    "sdWidth": "full",
                    "enabled": true
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
                "ednote": {
                    "sdWidth": "full",
                    "order": 13,
                    "enabled": false
                },
                "category": {
                    "field_name": "NTB Category",
                    "enabled": false
                },
                "subject_custom": {
                    "sdWidth": "full",
                    "field_name": "Subject",
                    "order": 11,
                    "enabled": false
                },
                "genre_custom": {
                    "sdWidth": "half",
                    "field_name": "Genre",
                    "order": 5,
                    "enabled": false
                }
            },
            "schema": {
                "ednote": {
                    "type": "string",
                    "required": false
                },
                "category": {
                    "type": "list",
                    "required": false
                },
                "subject_custom": {
                    "type": "list",
                    "mandatory_in_list": {
                        "scheme": {}
                    },
                    "schema": {},
                    "required": false
                },
                "genre_custom": {
                    "type": "list",
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
                    "required" : false,
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
        {"_id": "foo", "type": "picture"}
        """
        Then we get new resource
        When we post to "content_types"
        """
        {"_id": "bar", "type": "picture"}
        """
        Then we get error 400
        """
        {"_status": "ERR", "_issues": {"type": "Only 1 instance is allowed."}}
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
                "profile": "foo"
            }
          }]
        }
        """
        And there is no "headline" in data
        And there is no "language" in data

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
                    "enabled": false
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

    @auth
    Scenario: Language CV should not override language schema field
        Given "vocabularies"
        """
        [
            {
                "_id": "language",
                "display_name": "Language CV",
                "service": {"all": 1},
                "items": [{"name": "English", "qcode": "en"}]
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
                "language": {
                    "type": "string",
                    "required": false
                }
            },
            "editor": {
                "language": {
                    "enabled": false
                }
            }
        }
        """
        When we patch "/content_types/profile"
        """
        {
            "editor": {"language": {"enabled": true}}
        }
        """
        And we get "/content_types/profile"
        Then we get existing resource
        """
        {
            "editor": {"language": {"enabled": true}},
            "schema": {"language": {"type": "string"}}
        }
        """