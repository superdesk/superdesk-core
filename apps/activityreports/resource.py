from superdesk.resource import Resource


class ActivityReportResource(Resource):
    """Activity Report schema

    """

    schema = {
        'operation': {
            'type': 'string',
            'required': True,
            'allowed': ['publish', 'correct']
        },
        'date': {
            'type': 'datetime',
            'required': True
        },
        'desk': Resource.rel('desks', nullable=True),
    }

    item_methods = ['GET', 'PATCH', 'PUT', 'DELETE']
    resource_methods = ['GET', 'POST', 'DELETE']
    privileges = {'POST': 'activityreports', 'PATCH': 'activityreports', 'DELETE': 'activityreports'}
