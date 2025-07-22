from superdesk.resource import Resource


class ExportResource(Resource):
    """Export schema"""

    endpoint_name = "export"
    resource_methods = ["POST"]
    item_methods = []
    resource_title = endpoint_name
    schema = {
        "item_ids": {"type": "list", "required": True},
        "format_type": {"type": "string", "required": True},
        "validate": {"type": "boolean", "required": False},
        "inline": {"type": "boolean", "required": False, "default": False},
        "failures": {
            "type": "integer",
            "readonly": True,
        },
        "url": {
            "type": "string",
            "nullable": True,
        },
        "export": {
            "type": "dict",
            "readonly": True,
        },
    }
    privileges = {"POST": "archive"}
