import superdesk
from superdesk import get_resource_service
from .resource import Resource
from .services import BaseService
from flask import current_app as app


def init_app(app):
    endpoint_name = 'sequences'
    service = SequencesService(endpoint_name, backend=superdesk.get_backend())
    SequencesResource(endpoint_name, app=app, service=service)


class SequencesResource(Resource):
    schema = {
        'name': {
            'type': 'string',
            'required': True,
            'nullable': False,
            'empty': False,
            'iunique': True
        },
        'sequence_number': {
            'type': 'number',
            'default': 0,
        },
    }
    etag_ignore_fields = ['sequence_number', 'name']
    internal_resource = True


class SequencesService(BaseService):

    def get_next_sequence_number_for_item(
        self,
        resource_name,
        query_value,
        max_seq_number=None,
        min_seq_number=0,
        query_field='_id',
        sequence_field='sequence_number'
    ):
        """
        Generates Sequence Number
        :param resource_name: target resource
        :param query_value: value of field to query target item (ie target item id by default)
        :param query_field: default '_id', name of field to query target item
        :param max_seq_number: default $MAX_VALUE_OF_PUBLISH_SEQUENCE, maximal possible value
        :param min_seq_number: default 0, minimal possible value
        :param sequence_field: default 'sequence_number', name of field to store sequence number in the target item
        :returns: sequence_number
        """
        if not max_seq_number:
            max_seq_number = app.config['MAX_VALUE_OF_PUBLISH_SEQUENCE']

        target_resource = get_resource_service(resource_name)
        target_item = target_resource.find_one(**{
            'req': None,
            query_field: query_value
        })
        if target_item:
            sequence_number = target_item.get(sequence_field) or min_seq_number
        else:
            target_resource.create([{
                query_field: query_value,
                sequence_field: min_seq_number
            }, ])
            sequence_number = min_seq_number

        if (min_seq_number <= sequence_number + 1 <= max_seq_number):
            target_resource.find_and_modify(
                query={query_field: query_value},
                update={'$inc': {sequence_field: 1}},
                upsert=False
            )
        else:
            target_resource.find_and_modify(
                query={query_field: query_value},
                update={sequence_field: min_seq_number},
                upsert=False
            )

        return sequence_number

    def get_next_sequence_number_for_key(self, key_name, **kwargs):
        return self.get_next_sequence_number_for_item(
            resource_name='sequences',
            query_value=key_name,
            query_field='name',
            **kwargs
        )
