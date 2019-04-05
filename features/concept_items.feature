Feature: Concept items

    @auth
    Scenario: Create a concept item: success
        Given "vocabularies"
        """
        [{
            "_id" : "languages",
            "display_name" : "Languages",
            "type" : "manageable",
            "unique_field" : "qcode",
            "service" : {
                "all" : 1
            },
            "items" : [
                {
                    "name" : "en",
                    "qcode" : "en",
                    "is_active" : true
                },
                {
                    "name" : "es",
                    "qcode" : "es",
                    "is_active" : true
                }
            ]
        }]
        """
        Given empty "concept_items"
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien"],
            "language": "en",
            "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get response code 201
        When we get "/concept_items"
        Then we get existing resource
        """
        {
            "_items": [
                {
                    "_id": "#concept_items._id#",
                    "group_id": "#concept_items.group_id#",
                    "name": "Hobbit",
                    "cpnat_type": "cpnat:abstract",
                    "labels": [
                        "book",
                        "tolkien"
                    ],
                    "language": "en",
                    "definition_text": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien.",
                    "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien.",
                    "_updated": "__any_value__",
                    "_created": "__any_value__",
                    "created_by": "#CONTEXT_USER_ID#",
                    "_etag": "__any_value__"
                }
            ]
        }
        """
        When we get "/concept_items/#concept_items._id#"
        Then we get response code 200
        When we get "/concept_items/#concept_items._id#"
        Then we get existing resource
        """
        {
            "_id": "#concept_items._id#",
            "group_id": "__any_value__",
            "name": "Hobbit",
            "cpnat_type": "cpnat:abstract",
            "labels": [
                "book",
                "tolkien"
            ],
            "language": "en",
            "definition_text": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien.",
            "_updated": "__any_value__",
            "_created": "__any_value__",
            "created_by": "#CONTEXT_USER_ID#",
            "_etag": "__any_value__"
        }
        """


    @auth
    Scenario: Create a concept item: no languages cv
        Given empty "concept_items"
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien"],
            "language": "en",
            "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get response code 400

    @auth
    Scenario: Create a concept item: no required fields
        Given "vocabularies"
        """
        [{
            "_id" : "languages",
            "display_name" : "Languages",
            "type" : "manageable",
            "unique_field" : "qcode",
            "service" : {
                "all" : 1
            },
            "items" : [
                {
                    "name" : "en",
                    "qcode" : "en",
                    "is_active" : true
                },
                {
                    "name" : "es",
                    "qcode" : "es",
                    "is_active" : true
                }
            ]
        }]
        """
        Given empty "concept_items"
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien"],
            "definition_text": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get error 400
        """
        {
            "_issues": {
                "language": {
                    "required": 1
                }
            }
        }
        """
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "language": "de",
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien"],
            "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get error 400
        """
        {
            "_issues": {
                "language": "unallowed value 'de'"
            }
        }
        """
        When we post to "/concept_items"
        """
        {
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien"],
            "language": "en",
            "definition_text": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get error 400
        """
        {
            "_issues": {
                "name": {
                    "required": 1
                }
            }
        }
        """
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien"],
            "language": "en"
        }
        """
        Then we get error 400
        """
        {
            "_status": "ERR",
            "_issues": {
                "definition_html": {
                    "required": 1
                }
            },
            "_error": {
                "code": 400,
                "message": "Insertion failure: 1 document(s) contain(s) error(s)"
            }
        }
        """
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "labels": ["book", "tolkien"],
            "language": "en",
            "definition_text": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get error 400
        """
        {
            "_issues": {
                "cpnat_type": {
                    "required": 1
                }
            }
        }
        """

    @auth
    Scenario: Create a concept item: duplicate labels
        Given "vocabularies"
        """
        [{
            "_id" : "languages",
            "display_name" : "Languages",
            "type" : "manageable",
            "unique_field" : "qcode",
            "service" : {
                "all" : 1
            },
            "items" : [
                {
                    "name" : "en",
                    "qcode" : "en",
                    "is_active" : true
                },
                {
                    "name" : "es",
                    "qcode" : "es",
                    "is_active" : true
                }
            ]
        }]
        """
        Given empty "concept_items"
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien", "book"],
            "language": "en",
            "definition_text": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get error 400
        """
        {
            "_issues": {
                "labels": "Must contain unique items only."
            }
        }
        """

    @auth
    Scenario: Create a concept item: wrong and not supported cpnat_type
        Given "vocabularies"
        """
        [{
            "_id" : "languages",
            "display_name" : "Languages",
            "type" : "manageable",
            "unique_field" : "qcode",
            "service" : {
                "all" : 1
            },
            "items" : [
                {
                    "name" : "en",
                    "qcode" : "en",
                    "is_active" : true
                },
                {
                    "name" : "es",
                    "qcode" : "es",
                    "is_active" : true
                }
            ]
        }]
        """
        Given empty "concept_items"
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "cpnat_type": "cpnat:books",
            "labels": ["book", "tolkien"],
            "language": "en",
            "definition_text": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get error 400
        """
        {
            "_issues": {
                "cpnat_type": "unallowed value cpnat:books"
            }
        }
        """
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "cpnat_type": "cpnat:person",
            "labels": ["book", "tolkien"],
            "language": "en",
            "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get error 400
        """
        {
            "_issues": {
                "cpnat_type": "concept type 'cpnat:person' is not supported"
            }
        }
        """

    @auth
    Scenario: Create a concept item: not allowed properties for cpnat:abstract
        Given "vocabularies"
        """
        [{
            "_id" : "languages",
            "display_name" : "Languages",
            "type" : "manageable",
            "unique_field" : "qcode",
            "service" : {
                "all" : 1
            },
            "items" : [
                {
                    "name" : "en",
                    "qcode" : "en",
                    "is_active" : true
                },
                {
                    "name" : "es",
                    "qcode" : "es",
                    "is_active" : true
                }
            ]
        }]
        """
        Given empty "concept_items"
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien"],
            "language": "en",
            "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien.",
            "properties": {
                "name": "Some name"
            }
        }
        """
        Then we get error 400
        """
        {
            "_issues": {
                "properties": "field is not supported when 'cpnat_type' is 'cpnat:abstract'"
            }
        }
        """

    @auth
    @app_init
    Scenario: Create a concept item: group_id in payload
        Given "vocabularies"
        """
        [{
            "_id" : "languages",
            "display_name" : "Languages",
            "type" : "manageable",
            "unique_field" : "qcode",
            "service" : {
                "all" : 1
            },
            "items" : [
                {
                    "name" : "en",
                    "qcode" : "en",
                    "is_active" : true
                },
                {
                    "name" : "es",
                    "qcode" : "es",
                    "is_active" : true
                }
            ]
        }]
        """
        Given empty "concept_items"
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "group_id": "5c62d77efe985ea36958fa3e",
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien"],
            "language": "en",
            "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get response code 201
        When we get "/concept_items"
        Then we get existing resource
        """
        {
            "_items": [
                {
                    "group_id": "5c62d77efe985ea36958fa3e",
                    "name": "Hobbit",
                    "cpnat_type": "cpnat:abstract",
                    "labels": [
                        "book",
                        "tolkien"
                    ],
                    "language": "en",
                    "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien.",
                    "definition_text": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien.",
                    "_updated": "__any_value__",
                    "_created": "__any_value__",
                    "created_by": "#CONTEXT_USER_ID#",
                    "_etag": "__any_value__"
                }
            ]
        }
        """
        When we get "/concept_items"
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "group_id": "5c62d77efe985ea36958fa3e",
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien"],
            "language": "en",
            "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get response code 409
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "group_id": "b615a998-544b-4c3f-b063-9ceccdd7c1dc",
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien"],
            "language": "es",
            "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get response code 201

    @auth
    @app_init
    Scenario: Patch a concept item
        Given "vocabularies"
        """
        [{
            "_id" : "languages",
            "display_name" : "Languages",
            "type" : "manageable",
            "unique_field" : "qcode",
            "service" : {
                "all" : 1
            },
            "items" : [
                {
                    "name" : "en",
                    "qcode" : "en",
                    "is_active" : true
                },
                {
                    "name" : "es",
                    "qcode" : "es",
                    "is_active" : true
                }
            ]
        }]
        """
        Given empty "concept_items"
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien"],
            "language": "en",
            "group_id": "5c94ebcdfe985e1c9fc26d52",
            "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        Then we get response code 201
        When we patch "/concept_items/#concept_items._id#"
        """
        {"name": "Lord of the Rings"}
        """
        Then we get updated response
        """
        {
            "_created": "__any_value__",
            "_id": "#concept_items._id#",
            "_status": "OK",
            "_type": "concept_items",
            "_updated": "__any_value__",
            "group_id": "#concept_items.group_id#",
            "cpnat_type": "cpnat:abstract",
            "created_by": "#CONTEXT_USER_ID#",
            "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien.",
            "definition_text": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien.",
            "labels": [
                "book",
                "tolkien"
            ],
            "language": "en",
            "name": "Lord of the Rings",
            "updated_by": "#CONTEXT_USER_ID#"
        }
        """
        When we patch "/concept_items/#concept_items._id#"
        """
        {"properties": {}}
        """
        Then we get error 400
        """
        {
            "_issues": {"validator exception": "400: Request is not valid"}
        }
        """
        When we patch "/concept_items/#concept_items._id#"
        """
        {"cpnat_type": "cpnat:person"}
        """
        Then we get error 400
        """
        {
            "_issues": {"validator exception": "400: Request is not valid"}
        }
        """
        When we post to "/concept_items"
        """
        {
            "name": "Hobbit",
            "cpnat_type": "cpnat:abstract",
            "labels": ["book", "tolkien"],
            "group_id": "5c94ebcdfe985e1c9fc26d52",
            "language": "es",
            "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
        }
        """
        When we get "/concept_items"
        When we patch "/concept_items/#concept_items._id#"
        """
        {"language": "en"}
        """
        Then we get response code 400

        @auth
        Scenario: Put a concept item
            Given "vocabularies"
            """
            [{
                "_id" : "languages",
                "display_name" : "Languages",
                "type" : "manageable",
                "unique_field" : "qcode",
                "service" : {
                    "all" : 1
                },
                "items" : [
                    {
                        "name" : "en",
                        "qcode" : "en",
                        "is_active" : true
                    },
                    {
                        "name" : "es",
                        "qcode" : "es",
                        "is_active" : true
                    }
                ]
            }]
            """
            Given empty "concept_items"
            When we post to "/concept_items"
            """
            {
                "name": "Hobbit",
                "cpnat_type": "cpnat:abstract",
                "labels": ["book", "tolkien"],
                "language": "en",
                "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
            }
            """
            Then we get response code 201
            When we put to "/concept_items/#concept_items._id#"
            """
            {
                "name": "Lord of the Rings",
                "cpnat_type": "cpnat:abstract",
                "group_id": "#concept_items._id#",
                "labels": ["book", "tolkien", "fantasy"],
                "language": "es",
                "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
            }
            """
            Then we get updated response
            """
            {
                "_created": "__any_value__",
                "_id": "#concept_items._id#",
                "_status": "OK",
                "_updated": "__any_value__",
                "group_id": "#concept_items._id#",
                "cpnat_type": "cpnat:abstract",
                "created_by": "#CONTEXT_USER_ID#",
                "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien.",
                "definition_text": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien.",
                "labels": [
                    "book",
                    "tolkien",
                    "fantasy"
                ],
                "language": "es",
                "name": "Lord of the Rings",
                "updated_by": "#CONTEXT_USER_ID#"
            }
            """

        @auth
        Scenario: Delete a concept item
            Given "vocabularies"
            """
            [{
                "_id" : "languages",
                "display_name" : "Languages",
                "type" : "manageable",
                "unique_field" : "qcode",
                "service" : {
                    "all" : 1
                },
                "items" : [
                    {
                        "name" : "en",
                        "qcode" : "en",
                        "is_active" : true
                    },
                    {
                        "name" : "es",
                        "qcode" : "es",
                        "is_active" : true
                    }
                ]
            }]
            """
            Given empty "concept_items"
            When we post to "/concept_items"
            """
            {
                "name": "Hobbit",
                "cpnat_type": "cpnat:abstract",
                "labels": ["book", "tolkien"],
                "language": "en",
                "definition_html": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien."
            }
            """
            Then we get response code 201
            When we delete "/concept_items/#concept_items._id#"
            Then we get response code 204

        @auth
        Scenario: Fill definition_text from definition_html during creation and update
            Given "vocabularies"
            """
            [{
                "_id" : "languages",
                "display_name" : "Languages",
                "type" : "manageable",
                "unique_field" : "qcode",
                "service" : {
                    "all" : 1
                },
                "items" : [
                    {
                        "name" : "en",
                        "qcode" : "en",
                        "is_active" : true
                    },
                    {
                        "name" : "es",
                        "qcode" : "es",
                        "is_active" : true
                    }
                ]
            }]
            """
            Given empty "concept_items"
            When we post to "/concept_items"
            """
            {
                "name": "Hobbit",
                "cpnat_type": "cpnat:abstract",
                "labels": ["book", "tolkien"],
                "language": "en",
                "definition_html": "<p>The book.</p><p><b>The Hobbit</b> is a <span>children's <i>fantasy</i></span> novel by English author J. R. R. Tolkien.</p>"
            }
            """
            Then we get response code 201
            When we get "/concept_items"
            Then we get existing resource
            """
            {
                "_items": [
                    {
                        "_id": "#concept_items._id#",
                        "group_id": "__any_value__",
                        "name": "Hobbit",
                        "cpnat_type": "cpnat:abstract",
                        "labels": [
                            "book",
                            "tolkien"
                        ],
                        "language": "en",
                        "definition_html": "<p>The book.</p><p><b>The Hobbit</b> is a <span>children's <i>fantasy</i></span> novel by English author J. R. R. Tolkien.</p>",
                        "definition_text": "The book.\nThe Hobbit is a children's fantasy novel by English author J. R. R. Tolkien.",
                        "_updated": "__any_value__",
                        "_created": "__any_value__",
                        "created_by": "#CONTEXT_USER_ID#",
                        "_etag": "__any_value__"
                    }
                ]
            }
            """
            When we put to "/concept_items/#concept_items._id#"
            """
            {
                "name": "Lord of the Rings",
                "cpnat_type": "cpnat:abstract",
                "group_id": "#concept_items._id#",
                "labels": ["book", "tolkien", "fantasy"],
                "language": "es",
                "definition_html": "<p><b>The Hobbit</b> is a <span>children's <i>fantasy</i></span> novel by English author J. R. R. Tolkien.</p>"
            }
            """
            Then we get updated response
            """
            {
                "_created": "__any_value__",
                "_id": "#concept_items._id#",
                "_status": "OK",
                "_updated": "__any_value__",
                "group_id": "#concept_items._id#",
                "cpnat_type": "cpnat:abstract",
                "created_by": "#CONTEXT_USER_ID#",
                "definition_html": "<p><b>The Hobbit</b> is a <span>children's <i>fantasy</i></span> novel by English author J. R. R. Tolkien.</p>",
                "definition_text": "The Hobbit is a children's fantasy novel by English author J. R. R. Tolkien.",
                "labels": [
                    "book",
                    "tolkien",
                    "fantasy"
                ],
                "language": "es",
                "name": "Lord of the Rings",
                "updated_by": "#CONTEXT_USER_ID#"
            }
            """
            When we put to "/concept_items/#concept_items._id#"
            """
            {
                "name": "Lord of the Rings",
                "cpnat_type": "cpnat:abstract",
                "group_id": "#concept_items._id#",
                "labels": ["book", "tolkien", "fantasy"],
                "language": "es",
                "definition_html": "<p><b>The Hobbit II</b> is a <span>children's <i>fantasy</i></span> novel by English author J. R. R. Tolkien.</p>"
            }
            """
            Then we get updated response
            """
            {
                "_created": "__any_value__",
                "_id": "#concept_items._id#",
                "_status": "OK",
                "_updated": "__any_value__",
                "group_id": "#concept_items._id#",
                "cpnat_type": "cpnat:abstract",
                "created_by": "#CONTEXT_USER_ID#",
                "definition_html": "<p><b>The Hobbit II</b> is a <span>children's <i>fantasy</i></span> novel by English author J. R. R. Tolkien.</p>",
                "definition_text": "The Hobbit II is a children's fantasy novel by English author J. R. R. Tolkien.",
                "labels": [
                    "book",
                    "tolkien",
                    "fantasy"
                ],
                "language": "es",
                "name": "Lord of the Rings",
                "updated_by": "#CONTEXT_USER_ID#"
            }
            """
            When we patch "/concept_items/#concept_items._id#"
            """
            {"definition_html": "<p><b>Silmarillion</b></p>"}
            """
            Then we get updated response
            """
            {
                "_created": "__any_value__",
                "_id": "#concept_items._id#",
                "_status": "OK",
                "_updated": "__any_value__",
                "group_id": "#concept_items._id#",
                "cpnat_type": "cpnat:abstract",
                "created_by": "#CONTEXT_USER_ID#",
                "definition_html": "<p><b>Silmarillion</b></p>",
                "definition_text": "Silmarillion",
                "labels": [
                    "book",
                    "tolkien",
                    "fantasy"
                ],
                "language": "es",
                "name": "Lord of the Rings",
                "updated_by": "#CONTEXT_USER_ID#"
            }
            """
