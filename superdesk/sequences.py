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
        'key': {
            'type': 'string',
            'required': True,
            'nullable': False,
            'empty': False,
            'iunique': True
        },
        'sequence_number': {
            'type': 'number',
            'default': 1,
        },
    }
    etag_ignore_fields = ['sequence_number', 'name']
    internal_resource = True


class SequencesService(BaseService):

    def get_next_sequence_number(
        self,
        key_name,
        max_seq_number=None,
        min_seq_number=1
    ):
        """
        Generates Sequence Number
        :param key: key to identify the sequence
        :param max_seq_num: default $MAX_VALUE_OF_PUBLISH_SEQUENCE, maximal possible value
        :param min_seq_num: default 1, init value, sequence will start from the NEXT one
        :returns: sequence number
        """
        if not max_seq_number:
            max_seq_number = app.config['MAX_VALUE_OF_PUBLISH_SEQUENCE']

        target_resource = get_resource_service('sequences')
        sequence_number = target_resource.find_and_modify(
            query={'key': key_name},
            update={'$inc': {'sequence_number': 1}},
            upsert=True,
            new=True
        ).get('sequence_number')

        if not (min_seq_number <= sequence_number + 1 <= max_seq_number):
            target_resource.find_and_modify(
                query={'key': key_name, 'sequence_number': sequence_number},
                update={'sequence_number': min_seq_number},
                upsert=True
            )

        return sequence_number
