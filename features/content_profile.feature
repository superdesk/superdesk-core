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
        {"_id": "foo", "label": "Foo", "enabled": true, "updated_by": "#CONTEXT_USER_ID#"}
        """

    @auth
    Scenario: User can update profile
        Given "content_types"
        """
        [{"_id": "foo", "label": "Foo"}]
        """
        When we patch "content_types/foo"
        """
        {"label": "Bar"}
        """
        Then we get updated response
        """
        {"updated_by": "#CONTEXT_USER_ID#"}
        """
