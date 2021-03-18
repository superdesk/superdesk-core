import superdesk
import traceback
from superdesk import get_resource_service
from .resource import Resource
from .services import BaseService
import logging


logger = logging.getLogger(__name__)


def init_app(app) -> None:
    endpoint_name = "sequences"
    service = SequencesService(endpoint_name, backend=superdesk.get_backend())
    SequencesResource(endpoint_name, app=app, service=service)


class SequencesResource(Resource):
    schema = {
        "key": {"type": "string", "required": True, "nullable": False, "empty": False, "iunique": True},
        "sequence_number": {
            "type": "number",
            "default": 1,
        },
    }
    etag_ignore_fields = ["sequence_number", "name"]
    internal_resource = True
    mongo_indexes = {
        "key_1": ([("key", 1)], {"unique": True}),
    }


class SequencesService(BaseService):
    def get_next_sequence_number(self, key_name, max_seq_number=None, min_seq_number=1):
        """
        Generates Sequence Number

        :param key: key to identify the sequence
        :param max_seq_num: default None, maximal possible value, None means no upper limit
        :param min_seq_num: default 1, init value, sequence will start from the NEXT one
        :returns: sequence number
        """
        if not key_name:
            logger.error("Empty sequence key is used: {}".format("\n".join(traceback.format_stack())))
            raise KeyError("Sequence key cannot be empty")

        target_resource = get_resource_service("sequences")
        sequence_number = target_resource.find_and_modify(
            query={"key": key_name}, update={"$inc": {"sequence_number": 1}}, upsert=True, new=True
        ).get("sequence_number")

        if max_seq_number:
            if sequence_number > max_seq_number:
                target_resource.find_and_modify(
                    query={"key": key_name}, update={"$set": {"sequence_number": min_seq_number}}
                )

                sequence_number = min_seq_number

        return sequence_number
