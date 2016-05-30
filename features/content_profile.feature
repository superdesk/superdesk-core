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
            "updated_by": "#CONTEXT_USER_ID#",
            "schema": {
                "headline": {},
                "slugline": {},
                "genre": {},
                "anpa_take_key": {},
                "place": {},
                "priority": {},
                "urgency": {},
                "anpa_category": {},
                "subject": {},
                "ednote": {},
                "abstract": {},
                "body_html": {},
                "byline": {},
                "dateline": {},
                "located": {},
                "sign_off": {}
            }
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