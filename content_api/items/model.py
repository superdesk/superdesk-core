from typing import Annotated, Any
from datetime import datetime
from enum import Enum, unique

from pydantic import Field, field_validator

from superdesk.core.resources import ResourceModel, dataclass, fields, validators, ModelWithVersions


ContentAssociation = Annotated[
    dict[str, Any],
    fields.elastic_mapping(
        {
            "dynamic": False,
            "properties": {
                "featuremedia": {
                    "dynamic": False,
                    "properties": {
                        "_id": {"type": "keyword"},
                        "guid": {"type": "keyword"},
                        "unique_id": {"type": "integer"},
                    },
                },
            },
        }
    ),
]


@dataclass
class CVItem:
    qcode: fields.Keyword
    name: fields.Keyword
    schema: fields.Keyword | None = None


@dataclass
class CVItemWithCode:
    code: fields.Keyword
    name: fields.Keyword
    schema: fields.Keyword | None = None
    scheme: fields.Keyword | None = None


@dataclass
class Place:
    scheme: fields.Keyword | None = None
    qcode: fields.Keyword | None = None
    code: fields.Keyword | None = None
    name: fields.Keyword | None = None
    locality: fields.Keyword | None = None
    state: fields.Keyword | None = None
    country: fields.Keyword | None = None
    world_region: fields.Keyword | None = None
    locality_code: fields.Keyword | None = None
    state_code: fields.Keyword | None = None
    country_code: fields.Keyword | None = None
    world_region_code: fields.Keyword | None = None
    feature_class: fields.Keyword | None = None
    location: fields.Geopoint | None = None
    rel: fields.Keyword | None = None


@dataclass
class Annotation:
    id: int
    type: fields.Keyword
    body: fields.Keyword


@dataclass
class ContentAuthor:
    uri: fields.Keyword | None = None
    parent: fields.Keyword | None = None
    name: fields.TextWithKeyword | None = None
    role: fields.Keyword | None = None
    jobtitle: dict | None = None
    sub_label: fields.TextWithKeyword | None = None
    biography: str | None = None
    code: fields.Keyword | None = None


@dataclass
class ContentReference:
    id: Annotated[fields.Keyword, Field(alias="_id")]
    key: fields.Keyword | None = None
    uri: fields.Keyword | None = None
    guid: fields.Keyword | None = None
    type: fields.Keyword | None = None
    source: fields.Keyword | None = None


@unique
class PubStatusType(str, Enum):
    USABLE = "usable"
    WITHHELD = "withheld"
    CANCELLED = "canceled"


@unique
class ContentType(str, Enum):
    TEXT = "text"
    PREFORMATTED = "preformatted"
    AUDIO = "audio"
    VIDEO = "video"
    PICTURE = "picture"
    GRAPHIC = "graphic"
    COMPOSITE = "composite"


class ContentAPIItem(ResourceModel, ModelWithVersions):
    id: Annotated[str, Field(alias="_id")]
    associations: ContentAssociation | None = None
    anpa_category: list[CVItem] = Field(default_factory=list)
    body_html: fields.HTML | None = None
    body_text: str | None = None
    byline: str | None = None
    copyrightnotice: Annotated[str | None, fields.not_indexed()] = None
    copyrightholder: str | None = None
    description_html: str | None = None
    description_text: str | None = None
    headline: fields.HTML | None = None
    language: fields.Keyword | None = None
    located: str | None = None
    mimetype: fields.Keyword | None = None
    organization: list[dict] = Field(default_factory=list)
    person: list[dict] = Field(default_factory=list)
    place: list[Place] = Field(default_factory=list)
    profile: str | None = None
    pubstatus: Annotated[PubStatusType | None, fields.keyword_mapping()] = None
    renditions: dict | None = None
    service: list[CVItemWithCode] = Field(default_factory=list)
    slugline: str | None = None
    source: fields.Keyword | None = None
    subject: list[CVItemWithCode] = Field(default_factory=list)
    keywords: list[fields.HTML] = Field(default_factory=list)
    anpa_take_key: str | None = None

    content_type: Annotated[ContentType, fields.keyword_mapping(), Field(alias="type")] = ContentType.TEXT

    urgency: int | None = None
    priority: int | None = None
    uri: Annotated[fields.Keyword | None, validators.validate_iunique_value_async("items", "uri")] = None
    usageterms: str | None = None
    version: str | None = None
    versioncreated: datetime = Field(
        default_factory=datetime.now
    )
    firstcreated: datetime = Field(
        default_factory=datetime.now
    )
    firstpublished: datetime = Field(
        default_factory=datetime.now
    )
    embargoed: datetime | None = None
    evolvedfrom: fields.Keyword | None = None
    nextversion: fields.Keyword | None = None
    original_id: fields.Keyword | None = None
    subscribers: Annotated[list[fields.Keyword], fields.keyword_mapping(), Field(default_factory=list)]
    ednote: str | None = None
    signal: list[CVItemWithCode] = Field(default_factory=list)
    genre: list[CVItemWithCode] = Field(default_factory=list)
    ancestors: Annotated[list[fields.Keyword], fields.keyword_mapping(), Field(default_factory=list)]
    attachments: list[dict] = Field(default_factory=list)
    annotations: list[Annotation] = Field(default_factory=list)

    extra: dict | None = None
    extra_items: dict | None = None
    authors: list[ContentAuthor] = Field(default_factory=list)
    wordcount: int | None = None
    charcount: int | None = None
    readtime: int | None = None

    # These are for linking to Planning module resources
    event_id: fields.Keyword | None = None
    planning_id: fields.Keyword | None = None
    coverage_id: fields.Keyword | None = None
    agenda_id: fields.Keyword | None = None
    agenda_href: fields.Keyword | None = None

    refs: list[ContentReference] = Field(
        default_factory=list
    )
    expiry: datetime = Field(default_factory=datetime.now)

    @field_validator("version", mode="before")
    def parse_version(cls, value: int | str | None) -> str | None:
        return str(value) if value is not None else None
