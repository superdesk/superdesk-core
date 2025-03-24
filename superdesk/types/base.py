# This file is part of Superdesk
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
from datetime import datetime
from enum import Enum, unique
from typing import Annotated, Any

from pydantic import Field

from superdesk.core.resources import (
    Dataclass,
    ResourceModel,
    dataclass,
    fields,
    validators,
)
from superdesk.core.resources.validators import (
    validate_data_relation_async,
    validate_minlength,
    validate_unique_value_async,
)
from superdesk.metadata.item import FORMATS
from superdesk.utc import utcnow

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
class CVItem(Dataclass):
    qcode: fields.Keyword
    name: fields.Keyword
    scheme: fields.Keyword | None = None
    schema: fields.Keyword | None = None


@dataclass
class CVItemWithCode(Dataclass):
    code: fields.Keyword
    name: fields.Keyword
    schema: fields.Keyword | None = None
    scheme: fields.Keyword | None = None


@dataclass
class Place(Dataclass):
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
    continent_code: fields.Keyword | None = None
    region: fields.Keyword | None = None
    region_code: fields.Keyword | None = None
    tz: fields.Keyword | None = None


@dataclass
class Annotation(Dataclass):
    id: int
    type: fields.Keyword
    body: fields.Keyword


@dataclass
class ContentAuthor(Dataclass):
    uri: fields.Keyword | None = None
    parent: fields.Keyword | None = None
    name: fields.TextWithKeyword | None = None
    role: fields.Keyword | None = None
    jobtitle: dict | None = None
    sub_label: fields.TextWithKeyword | None = None
    biography: str | None = None
    code: fields.Keyword | None = None


@dataclass
class ContentReference(Dataclass):
    id: Annotated[fields.Keyword, Field(alias="_id")]
    key: fields.Keyword | None = None
    uri: fields.Keyword | None = None
    guid: fields.Keyword | None = None
    type: fields.Keyword | None = None
    source: fields.Keyword | None = None


@unique
class ContentType(str, Enum):
    TEXT = "text"
    PREFORMATTED = "preformatted"
    AUDIO = "audio"
    VIDEO = "video"
    PICTURE = "picture"
    GRAPHIC = "graphic"
    COMPOSITE = "composite"


@unique
class PubStatusType(str, Enum):
    USABLE = "usable"
    HOLD = "withheld"
    CANCELED = "canceled"


@dataclass
class Genre:
    qcode: str
    name: str


@dataclass
class CompanyCodes:
    qcode: str
    name: str
    security_exchange: str


@unique
class ContentTypes(str, Enum):
    TEXT = "text"
    PREFORMATTED = "preformatted"
    AUDIO = "audio"
    VIDEO = "video"
    PICTURE = "picture"
    GRAPHIC = "graphic"
    COMPOSITE = "composite"
    EVENT = "event"
    PLANNING = "planning"


class ContentStates(fields.Keyword, Enum):
    DRAFT = "draft"
    INGESTED = "ingested"
    ROUTED = "routed"
    FETCHED = "fetched"
    SUBMITTED = "submitted"
    IN_PROGRESS = "in_progress"
    SPIKED = "spiked"
    PUBLISHED = "published"
    KILLED = "killed"
    CORRECTED = "corrected"
    SCHEDULED = "scheduled"
    RECALLED = "recalled"
    UNPUBLISHED = "unpublished"
    CORRECTION = "correction"
    BEING_CORRECTED = "being_corrected"


@dataclass
class Subject:
    qcode: str
    name: str
    scheme: str | None = None


@dataclass
class GroupRefRefs:
    idRef: fields.Keyword
    residRef: fields.Keyword
    _id: fields.Keyword
    uri: fields.Keyword
    guid: fields.Keyword
    type: fields.Keyword
    location: fields.Keyword
    headline: str
    slugline: str
    _current_version: int | None = None


@dataclass
class GroupRef:
    id: str
    refs: list[GroupRefRefs]


@dataclass
class EntityMetadata:
    name: fields.TextWithKeyword
    qcode: fields.Keyword
    scheme: fields.Keyword
    source: fields.Keyword


@dataclass
class LinkedInPackage:
    package: Annotated[str, validate_data_relation_async("archive")]
    package_type: str | None = Field(None, deprecated=True)


@dataclass
class Located:
    state_code: str
    city: str
    tz: str
    country_code: str
    dateline: str
    alt_name: str
    state: str
    city_code: str
    country: str
    code: str
    scheme: str
    location: fields.Geopoint | None = None
    place: Place | None = None


@dataclass
class Dateline:
    source: str
    located: Located | None = None
    date: datetime | None = None
    text: str | None = None


@dataclass
class POI:
    x: float
    y: float


@dataclass
class MarkedDesk:
    desk_id: Annotated[fields.ObjectId | None, validate_data_relation_async("desks")] = None
    date_marked: datetime | None = None
    user_marked: Annotated[fields.ObjectId | None, validate_data_relation_async("users")] = None
    date_acknowledged: datetime | None = None
    user_acknowledged: Annotated[fields.ObjectId | None, validate_data_relation_async("users")] = None


@dataclass
class Flag:
    marked_for_not_publication: bool = False
    marked_for_legal: bool = False
    marked_archived_only: bool = False
    marked_for_sms: bool = False


@dataclass
class Attachment:
    attachment: fields.ObjectId | None = None


@dataclass
class ScheduleSettings:
    time_zone: str | None = None
    utc_publish_schedule: datetime | None = None
    utc_embargo: datetime | None = None


@dataclass
class Broadcast:
    status: fields.Keyword
    master_id: fields.Keyword
    rewrite_id: fields.Keyword


@dataclass
class Task:
    desk_history: list[fields.Keyword]
    last_desk: fields.Keyword
    status: fields.Keyword
    last_authoring_desk: fields.Keyword
    last_production_desk: fields.Keyword
    user: fields.Keyword | None = None
    desk: fields.Keyword | None = None
    stage: fields.Keyword | None = None


@dataclass
class TargetRegion:
    qcode: str
    name: str
    allow: bool


@dataclass
class TargetType:
    qcode: str
    name: str
    allow: bool


class ItemOperation(Enum):
    CREATE = "create"
    FETCH = "fetch"
    UPDATE = "update"
    RESTORE = "restore"
    DUPLICATE = "duplicate"
    DUPLICATED_FROM = "duplicated_from"
    DESCHEDULE = "deschedule"
    REWRITE = "rewrite"
    LINK = "link"
    UNLINK = "unlink"
    MARK = "mark"
    UNMARK = "unmark"
    RESEND = "resend"
    EXPORT_HIGHLIGHT = "export_highlight"
    CREATE_HIGHLIGHT = "create_highlight"


class ItemSchema(ResourceModel):
    old_version: int
    last_version: int
    task: Task
    publish_schedule: datetime | None = None
    schedule_settings: ScheduleSettings | None = None
    operation: ItemOperation
    event_id: fields.Keyword
    rewritten_by: fields.Keyword | None = None
    rewrite_of: fields.Keyword | None = None
    sequence: int | None = Field(None, deprecated=True)
    associated_take_sequence: int | None = Field(None, deprecated=True)
    embargo: datetime | None = None
    broadcast: Broadcast | None = None
    expiry_status: str | None = None
    original_id: fields.Keyword


class BaseContentItem(ResourceModel):
    id: Annotated[str, Field(alias="_id"), validate_unique_value_async(field_name="_id")]
    guid: Annotated[str | None, validate_unique_value_async(field_name="guid")] = None
    uri: Annotated[fields.Keyword | None, validators.validate_iunique_value_async("items", "uri")] = None
    versioncreated: datetime = Field(default_factory=utcnow)
    firstcreated: datetime = Field(default_factory=utcnow)
    firstpublished: datetime = Field(default_factory=utcnow)
    pubstatus: Annotated[PubStatusType | None, fields.keyword_mapping()] = None
    anpa_category: list[CVItem] = Field(default_factory=list)
    # FIXME! incompatibilities between MetadataResource and ContentAPIItem
    # version: str | None = None
    # genre: list[CVItemWithCode] = Field(default_factory=list)
    # signal: list[CVItemWithCode] = Field(default_factory=list)
    # place: list[Place] = Field(default_factory=list)
    annotations: list[Annotation] = Field(default_factory=list)
    authors: list[ContentAuthor] = Field(default_factory=list)
    body_html: fields.HTML | None = None
    body_text: fields.HTML | None = None
    headline: fields.HTML | None = None
    byline: fields.HTML | None = None
    description_text: fields.HTML | None = None
    usageterms: str | None = None
    copyrightnotice: Annotated[str | None, fields.not_indexed()] = None
    copyrightholder: str | None = None
    language: fields.Keyword | None = None
    urgency: int | None = None
    priority: int | None = None
    embargoed: datetime | None = None
    expiry: datetime | None = None
    associations: ContentAssociation | None = None
    refs: list[ContentReference] = Field(default_factory=list)
    extra: dict | None = None


class MetadataResource(BaseContentItem):
    unique_id: Annotated[int, validate_unique_value_async(field_name="unique_id")]
    unique_name: Annotated[fields.Keyword, validate_unique_value_async(field_name="unique_name")]
    version: int
    ingest_id: fields.Keyword | None = None
    ingest_version: fields.Keyword | None = None
    family_id: fields.Keyword | None = None
    related_to: fields.Keyword | None = None
    original_creator: Annotated[fields.ObjectId | None, validate_data_relation_async("users")] = None
    version_creator: Annotated[fields.ObjectId | None, validate_data_relation_async("users")] = None
    ingest_provider: Annotated[fields.ObjectId | None, validate_data_relation_async("ingest_providers")] = None
    source: fields.Keyword
    original_source: fields.Keyword
    ingest_provider_sequence: fields.Keyword
    subject: Annotated[list[Subject] | None, fields.nested_list(include_in_parent=True)] = None
    genre: list[Genre] | None = None
    company_codes: list[CompanyCodes] | None = None
    item_type: Annotated[ContentTypes, fields.keyword_mapping] = Field(ContentTypes.TEXT, alias="type")
    package_type: str | None = Field(None, deprecated=True)
    abstract: fields.HTML | None = None
    slugline: Annotated[
        str,
        fields.elastic_mapping(
            {
                "type": "string",
                "fielddata": True,
                "fields": {
                    "phrase": {
                        "type": "string",
                        "analyzer": "phrase_prefix_analyzer",
                        "fielddata": True,
                    },
                    "keyword": {
                        "type": "keyword",
                    },
                    "text": {"type": "string", "analyzer": "html_field_analyzer"},
                },
            }
        ),
    ]
    anpa_take_key: str | None = None
    correction_sequence: int | None = None
    rewrite_sequence: int | None = None
    # FIXME: duplicate of ItemSchema
    rewrite_of: fields.Keyword | None = None
    # FIXME: duplicate of ItemSchema
    rewritten_by: fields.Keyword | None = None
    # FIXME: duplicate of ItemSchema
    sequence: int | None = None
    keywords: Annotated[
        list[fields.Keyword], fields.elastic_mapping({"type": "list", "mapping": "html_field_analyzer"})
    ]
    word_count: int
    profile: fields.Keyword | None = None
    state: ContentStates
    revert_state: ContentStates | None = None
    signal: list[Subject] = Field(default_factory=list)
    ednote: fields.HTML | None = None
    archive_description: str | None = None
    groups: Annotated[list[GroupRef] | None, validate_minlength(1)] = None
    deleted_groups: Annotated[list[str] | None, validate_minlength(1)] = None
    dateline: Dateline | None = None
    # TODO-ASYNC: Add support for fileandmedia`
    media: fields.Keyword | None = None
    mimetype: fields.Keyword | None = None
    poi: POI | None = None
    renditions: dict[str, dict] = Field(default_factory=dict)
    filemeta: dict[str, dict] = Field(default_factory=dict)
    filemeta_json: Annotated[str | None, fields.not_indexed()] = None
    media_file: str
    contents: list
    alt_text: str | None = None
    # FIXME: Place is slightly different ("location" is not a list here)
    place: list[Place] | None = None
    event: list[EntityMetadata] = Field(default_factory=list)
    person: list[EntityMetadata] = Field(default_factory=list)
    object: list[EntityMetadata] = Field(default_factory=list)
    organisation: list[EntityMetadata] = Field(default_factory=list)
    creditline: str
    linked_in_packages: list[LinkedInPackage] | None = None
    highlight: Annotated[fields.ObjectId | None, validate_data_relation_async("highlights")] = None
    highlights: Annotated[list[fields.ObjectId] | None, validate_data_relation_async("highlights")] = None
    marked_desks: list[MarkedDesk] | None = None
    more_coming: bool = Field(False, deprecated=True)
    sign_off: fields.HTML | None = None
    # FIXME: duplicate of ItemSchema
    task: Task
    task_id: fields.Keyword | None = None
    lock_user: Annotated[fields.ObjectId | None, validate_data_relation_async("users")] = None
    lock_time: datetime | None = None
    lock_session: Annotated[fields.ObjectId | None, validate_data_relation_async("auth")] = None
    lock_action: fields.Keyword | None = None
    template: Annotated[fields.ObjectId | None, validate_data_relation_async("content_templates")] = None
    body_footer: Annotated[str | None, fields.not_indexed()] = None
    flags: Flag | None = None
    sms_message: str | None = None
    format: fields.Keyword = FORMATS.HTML
    auto_publish: bool = False
    fields_meta: dict[str, dict] | None = None
    attachments: Annotated[list[Attachment] | None, validate_data_relation_async("attachments")] = None
    assignment_id: fields.Keyword | None = None
    translated_from: fields.Keyword | None = None
    translation_id: fields.Keyword | None = None
    translations: list[str] | None = None
    processed_from: fields.Keyword | None = None
    embargoed_text: Annotated[str | None, fields.not_indexed()] = None
    marked_for_user: Annotated[fields.ObjectId | None, validate_data_relation_async("users")] = None
    marked_for_sign_off: str | None = None
    # FIXME: duplicate of ItemSchema
    broadcast: Broadcast | None = None
    event_id: fields.Keyword
    # FIXME: duplicate of ItemSchema
    embargo: datetime | None = None
    # FIXME: duplicate of ItemSchema
    publish_schedule: datetime | None = None
    # FIXME: duplicate of ItemSchema
    schedule_settings: ScheduleSettings | None = None
    used: bool = False
    used_count: int = 0
    used_updated: datetime
    metrics: dict[str, Any]
    # FIXME: conflict here with ItemSchema
    # operation: str | None = None
    es_highlight: dict[str, Any] | None = None
    target_regions: list[TargetRegion] | None = None
    target_types: list[TargetType] | None = None
    target_subscribers: list | None = None
    scope: fields.Keyword
