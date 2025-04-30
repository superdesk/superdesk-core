from pydantic import Field
from typing import Annotated
from datetime import datetime

from superdesk.utils import get_random_token
from superdesk.core.resources import ResourceModel, fields
from superdesk.core.resources.validators import validate_data_relation_async


class SubscriberToken(ResourceModel):
    id: Annotated[str, Field(alias="_id", default_factory=get_random_token)]
    expiry: datetime | None = None
    expiry_days: int | None = None
    subscriber: Annotated[fields.ObjectId, validate_data_relation_async("subscribers")]
