from typing import Annotated, Any
from pydantic import Field

from .enums import MonitoringTypeEnum, MonitoringViewEnum, DeskTypeEnum
from superdesk.core.resources import ResourceModel, fields, dataclass
from superdesk.core.resources.fields import ObjectId
from superdesk.core.resources.validators import validate_unique_value_async, validate_data_relation_async


@dataclass
class MonitoringSetting:
    _id: str
    type: MonitoringTypeEnum
    max_items: int


class DesksResourceModel(ResourceModel):
    name: Annotated[fields.Keyword, validate_unique_value_async("desks", "name")]
    description: str
    members: list[dict[str, Annotated[ObjectId, validate_data_relation_async("users")]]] = Field(default_factory=list)
    incoming_stage: Annotated[ObjectId, validate_data_relation_async("stages")] | None = None
    working_stage: Annotated[ObjectId, validate_data_relation_async("stages")] | None = None
    content_expiry: int
    source: str
    send_to_desk_not_allowed: bool = Field(default=False)
    monitoring_settings: list[MonitoringSetting] = Field(default_factory=list)
    desk_type: DeskTypeEnum = Field(default=DeskTypeEnum.AUTHORING)
    desk_metadata: dict[str, Any] = Field(default_factory=dict)
    content_profiles: dict[str, Any] = Field(default_factory=dict)
    desk_language: str
    monitoring_default_view: MonitoringViewEnum | None = None
    default_content_profile: Annotated[ObjectId, validate_data_relation_async("content_types")] | None = None
    default_content_template: Annotated[ObjectId, validate_data_relation_async("content_templates")] | None = None
    slack_channel_name: str = Field(description="Name of a Slack channel that may be associated with the desk")
    preferred_cv_items: dict[str, Any] = Field(default_factory=dict, description="Desk prefered vocabulary items")
    preserve_published_content: bool = Field(
        default=False,
        description="If the preserve_published_content is set to true then the content on this won't be expired",
    )
    sams_settings: dict[str, Any] = Field(
        default_factory=dict, description="Store SAMS's Desk settings on the Desk items"
    )
    email: str | None = None
