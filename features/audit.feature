Feature: Resource Audit Logs
    @auth
    @notification
    Scenario: Pydantic resources create audit logs
        When we post to "/filter_conditions" with success
        """
        [{"name": "sport", "field": "anpa_category", "operator": "in", "value": "4"}]
        """
        When we patch latest
        """
        {"name": "Sports Content", "field": "subject", "operator": "in", "value": "q"}
        """
        Then we get OK response
        When we delete latest
        Then we get OK response
        And we get audit logs
        """
        [{
            "resource": "filter_conditions",
            "action": "created",
            "user": "#CONTEXT_USER_ID#",
            "audit_id": "#filter_conditions._id#",
            "extra": {
                "name": "sport",
                "field": "anpa_category",
                "operator": "in",
                "value": "4"
            }
        }, {
            "resource": "filter_conditions",
            "action": "updated",
            "user": "#CONTEXT_USER_ID#",
            "audit_id": "#filter_conditions._id#"
        }, {
            "resource": "filter_conditions",
            "action": "deleted",
            "user": "#CONTEXT_USER_ID#",
            "audit_id": "#filter_conditions._id#"
        }]
        """
        And we get notifications
        """
        [{
            "event": "resource:created",
            "extra": {
                "resource": "filter_conditions",
                "_id": "#filter_conditions._id#"
            }
        }, {
            "event": "resource:updated",
            "extra": {
                "resource": "filter_conditions",
                "_id": "#filter_conditions._id#",
                "fields": {"name": 1, "value": 1, "field": 1}
            }
        }, {
            "event": "resource:deleted",
            "extra": {
                "resource": "filter_conditions",
                "_id": "#filter_conditions._id#"
            }
        }]
        """
