Feature: Product Tests
    @auth
    Scenario: Fails if the article does not exist
        When we post to "products/test"
        """
        {"article_id": "doesn't-exist"}
        """
        Then we get error 400
        """
        {"_status": "ERR", "_message": "Article not found"}
        """

    @auth
    Scenario: Product test endpoint
        Given "filter_conditions"
        """
        [
            {"name": "entertainment", "field": "anpa_category", "operator": "in", "value": "ent"},
            {"name": "finance", "field": "anpa_category", "operator": "in", "value": "fin"}
        ]
        """
        And "content_filters"
        """
        [
            {"name": "entertainment", "content_filter": [{"expression": {"fc": ["#filter_conditions_0._id#"]}}]},
            {"name": "finance", "content_filter": [{"expression": {"fc": ["#filter_conditions_1._id#"]}}]}
        ]
        """
        And "products"
        """
        [
            {
                "name":"entertainment-1", "codes":"abc,xyz", "product_type": "both",
                "content_filter": {"filter_id": "#content_filters_0._id#", "filter_type": "permitting"}
            },
            {
                "name":"finance-1", "codes":"abc,xyz", "product_type": "both",
                "content_filter": {"filter_id": "#content_filters_1._id#", "filter_type": "permitting"}
            }
        ]
        """

        When we post to "/archive"
        """
        [{"anpa_category": [{"qcode" : "ent", "name" : "Entertainment"}]}]
        """
        When we post to "products/test"
        """
        {"article_id": "#archive._id#"}
        """
        Then we get existing resource
        """
        {"_items": [
            {"product_id": "#products_0._id#", "matched": true},
            {"product_id": "#products_1._id#", "matched": false, "reason": "Story does not match the filter: finance"}
        ]}
        """

