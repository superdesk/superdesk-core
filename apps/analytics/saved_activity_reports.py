from superdesk.resource import Resource


class SavedActivityReportResource(Resource):
    """Saved Activity Report schema
    """

    schema = {
        'name': {
            'type': 'string',
            'required': True,
            'minlength': 1
        },
        'description': {
            'type': 'string'
        },
        'is_global': {
            'type': 'boolean',
            'default': False
        },
        'owner': Resource.rel('users', nullable=True),
        'operation': {
            'type': 'string',
            'required': True
        },
        'desk': Resource.rel('desks', nullable=True, required=True),
        'operation_date': {
            'type': 'datetime',
            'required': True
        },
        'subject': {
            'type': 'string'
        },
        'keywords': {
            'type': 'string'
        },
        'group_by': {
            'type': 'list'
        }
    }
    item_methods = ['GET', 'PATCH', 'PUT', 'DELETE']
    resource_methods = ['GET', 'POST']
    privileges = {'POST': 'activity_reports', 'PATCH': 'activity_reports',
                  'PUT': 'activity_reports', 'DELETE': 'activity_reports'}
