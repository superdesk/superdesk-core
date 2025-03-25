from typing import Annotated
from enum import Enum, unique

from pydantic import Field, field_validator

from superdesk.core.resources import fields, ModelWithVersions
from superdesk.types.base import BaseContentItem, CVItemWithCode, ContentType, Place
from superdesk.types.base import CVItem  # noqa - Imported from here by Planning and Newshub


@unique
class PubStatusType(str, Enum):
    USABLE = "usable"
    WITHHELD = "withheld"
    CANCELLED = "canceled"


class ContentAPIItem(BaseContentItem, ModelWithVersions):
    slugline: str | None = None
    description_html: str | None = None
    located: str | None = None
    mimetype: fields.Keyword | None = None
    organization: list[dict] = Field(default_factory=list)
    person: list[dict] = Field(default_factory=list)
    place: list[Place] = Field(default_factory=list)
    profile: str | None = None
    renditions: dict | None = None
    service: list[CVItemWithCode] = Field(default_factory=list)
    subject: list[CVItemWithCode] = Field(default_factory=list)
    source: fields.Keyword | None = None
    keywords: list[fields.HTML] = Field(default_factory=list)
    anpa_take_key: str | None = None

    content_type: Annotated[ContentType, fields.keyword_mapping(), Field(alias="type")] = ContentType.TEXT

    version: str | None = None
    evolvedfrom: fields.Keyword | None = None
    nextversion: fields.Keyword | None = None
    original_id: fields.Keyword | None = None
    subscribers: Annotated[list[fields.Keyword], fields.keyword_mapping(), Field(default_factory=list)]
    ednote: str | None = None
    signal: list[CVItemWithCode] = Field(default_factory=list)
    genre: list[CVItemWithCode] = Field(default_factory=list)
    ancestors: Annotated[list[fields.Keyword], fields.keyword_mapping(), Field(default_factory=list)]
    attachments: list[dict] = Field(default_factory=list)

    extra_items: dict | None = None
    wordcount: int | None = None
    charcount: int | None = None
    readtime: int | None = None

    # These are for linking to Planning module resources
    event_id: fields.Keyword | None = None
    planning_id: fields.Keyword | None = None
    coverage_id: fields.Keyword | None = None
    agenda_id: fields.Keyword | None = None
    agenda_href: fields.Keyword | None = None

    @field_validator("version", mode="before")
    def parse_version(cls, value: int | str | None) -> str | None:
        return str(value) if value is not None else None
