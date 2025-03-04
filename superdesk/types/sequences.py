from typing import Annotated

from superdesk.core.resources import ResourceModelWithObjectId
from superdesk.core.resources.validators import validate_data_relation_async


class SequencesResource(ResourceModelWithObjectId):
    key: Annotated[str, validate_data_relation_async("sequences", "key")]
    sequence_number: int = 1
