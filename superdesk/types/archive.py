# This file is part of Superdesk
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import datetime
from enum import Enum
from enum import Enum
from typing import Any

from pydantic import Field

from superdesk.core.resources import ResourceModel, dataclass
from superdesk.metadata.item import FORMATS


class ContentTypes(Enum):
    TEXT = "text"
    PREFORMATTED = "preformatted"
    AUDIO = "audio"
    VIDEO = "video"
    PICTURE = "picture"
    GRAPHIC = "graphic"
    COMPOSITE = "composite"
    EVENT = "event"
    PLANNING = "planning"


@dataclass
class ScheduleSettings:
    time_zone: str | None = None
    utc_publish_schedule: datetime | None = None
    utc_embargo: datetime | None = None


@dataclass
class Broadcast:
    status: str
    master_id: str
    rewrite_id: str


@dataclass
class Subject:
    qcode: str
    name: str
    scheme: str | None = None


@dataclass
class Genre:
    qcode: str
    name: str


@dataclass
class CompanyCodes:
    qcode: str
    name: str
    security_exchange: str


@dataclass
class Slugline:
    phrase: str
    keyword: str
    text: str


class ContentStates(Enum):
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


class PubStatuses(Enum):
    USABLE = "usable"
    HOLD = "withheld"
    CANCELED = "canceled"


@dataclass
class Author:
    uri: str
    parent: str
    name: str
    role: str
    jobtitle: str
    sub_label: str


@dataclass
class Geopoint:
    lat: float
    lon: float


@dataclass
class GroupRefRefs:
    idRef: str
    _id: str
    uri: str
    guid: str
    type: str
    location: str
    headline: str
    slugline: str


@dataclass
class GroupRef:
    id: str
    refs: GroupRefRefs


@dataclass
class Place:
    code: str
    name: str
    qcode: str
    scheme: str
    feature_class: str
    location: list[Geopoint]
    continent_code: str | None = None
    region: str | None = None
    region_code: str | None = None
    locality: str | None = None
    state: str | None = None
    country: str | None = None
    world_region: str | None = None
    locality_code: str | None = None
    state_code: str | None = None
    country_code: str | None = None
    world_region_code: str | None = None
    rel: str | None = None
    tz: str | None = None


@dataclass
class Ref:
    _id: str
    key: str
    uri: str
    guid: str
    type: str
    source: str | None = None


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
    location: list[Geopoint]
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
class FeatureMedia:
    _id: str
    guid: str
    unique_id: int


@dataclass
class Associations:
    featuremedia: FeatureMedia | None = None


@dataclass
class EntityMetadataItem:
    name: str
    qcode: str
    scheme: str
    source: str


@dataclass
class EntityMetadata:
    metadata: list[EntityMetadataItem] | None = None


@dataclass
class MarkedDesk:
    # FIXME: Resource.rel
    desk_id: str | None = None
    date_marked: datetime | None = None
    # FIXME: Resource.rel
    user_marked: str | None = None
    date_acknowledged: datetime | None = None
    # FIXME: Resource.rel
    user_acknowledged: str | None = None


@dataclass
class Flag:
    marked_for_not_publication: bool = False
    marked_for_legal: bool = False
    marked_archived_only: bool = False
    marked_for_sms: bool = False


@dataclass
class Annotation:
    id: int
    type: str
    body: str


@dataclass
class Attachment:
    pass


@dataclass
class Task:
    desk_history: list[str]
    last_desk: str
    status: str
    last_authoring_desk: str
    last_production_desk: str
    user: str | None = None
    desk: str | None = None
    stage: str | None = None


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
    event_id: str
    rewritten_by: str | None = None
    rewrite_of: str | None = None
    sequence: int | None = Field(None, deprecated=True)
    associated_take_sequence: int | None = Field(None, deprecated=True)
    embargo: datetime | None = None
    broadcast: Broadcast | None = None
    expiry_status: str | None = None
    original_id: str


class MetadataResource(ResourceModel):
    guid: str
    uri: str
    unique_id: int
    unique_name: str
    version: int
    ingest_id: str
    ingest_version: str
    family_id: str
    related_to: str
    # FIXME: Resource.rel
    original_creator: str | None = None
    # FIXME: Resource.rel
    version_creator: str | None = None
    firstcreated: datetime
    versioncreated: datetime
    firstpublished: datetime | None = None
    # FIXME: Resource.rel
    ingest_provider: str | None = None
    source: str
    original_source: str
    ingest_provider_sequence: str
    usageterms: str | None = None
    copyrightnotice: str | None = None
    copyrightholder: str | None = None
    anpa_category: list[Subject] | None = None
    subject: list[Subject]
    genre: list[Genre] | None = None
    company_codes: list[CompanyCodes] | None = None
    item_type: ContentTypes = Field(ContentTypes.TEXT, alias="type")
    package_type: str | None = Field(None, deprecated=True)
    language: str | None = None
    abstract: str | None = None
    headline: str | None = None
    slugline: Slugline
    anpa_take_key: str | None = None
    correction_sequence: int | None = None
    rewrite_sequence: int | None = None
    # FIXME: duplicate of ItemSchema
    rewrite_of: str | None = None
    # FIXME: duplicate of ItemSchema
    rewritten_by: str | None = None
    # FIXME: duplicate of ItemSchema
    sequence: int | None = None
    keywords: list[str]
    word_count: int
    priority: int | None = None
    urgency: int | None = None
    profile: str | None = None
    state: ContentStates
    revert_state: ContentStates | None = None
    pubstatus: PubStatuses | None = None
    signal: list[Subject]
    byline: str | None = None
    ednote: str | None = None
    authors: list[Author] | None = None
    description_text: str | None = None
    archive_description: str | None = None
    groups: list[GroupRef] | None = None
    deleted_groups: list[str] | None = None
    body_html: str | None = None
    body_text: str | None = None
    dateline: Dateline | None = None
    expiry: datetime
    # FIXME: type file
    media: str | None = None
    mimetype: str
    poi: POI
    renditions: dict[str, dict]
    filemeta: dict[str, dict]
    filemeta_json: str
    media_file: str
    contents: list
    associations: Associations
    refs: list[Ref]
    alt_text: str | None = None
    # FIXME: Place is slightly different ("location" is not a list here)
    place: list[Place] | None = None
    event: EntityMetadata | None = None
    person: EntityMetadata | None = None
    object: EntityMetadata | None = None
    organisation: EntityMetadata | None = None
    creditline: str
    # FIXME: Resource.rel
    linked_in_packages: list[dict[str, str]] | None = None
    # FIXME: Resource.rel
    highlight: str | None = None
    # FIXME: Resource.rel
    highlights: list[str] | None = None
    marked_desks: list[MarkedDesk] | None = None
    more_coming: bool = Field(False, deprecated=True)
    sign_off: str | None = None
    # FIXME: duplicate of ItemSchema
    task: Task
    task_id: str | None = None
    # FIXME: Resource.rel
    lock_user: str | None = None
    lock_time: datetime | None = None
    # FIXME: Resource.rel
    lock_session: str | None = None
    lock_action: str | None = None
    # FIXME: Resource.rel
    template: str | None = None
    body_footer: str | None = None
    flags: Flag | None = None
    sms_message: str | None = None
    format: str = FORMATS.HTML
    auto_publish: bool
    fields_meta: dict[str, dict] | None = None
    annotations: list[Annotation] | None = None
    extra: dict[str, Any] | None = None
    # FIXME: Resource.rel
    attachments: list[Attachment] | None = None
    assignment_id: str
    translated_from: str
    translation_id: str
    translations: list
    processed_from: str
    embargoed: datetime
    embargoed_text: str
    # FIXME: Resource.rel
    marked_for_user: str | None = None
    marked_for_sign_off: str | None = None
    # FIXME: duplicate of ItemSchema
    broadcast: Broadcast | None = None
    event_id: str
    # FIXME: duplicate of ItemSchema
    embargo: datetime | None = None
    # FIXME: duplicate of ItemSchema
    publish_schedule: datetime | None = None
    # FIXME: duplicate of ItemSchema
    schedule_settings: ScheduleSettings | None = None
    used: bool
    used_count: int
    used_updated: datetime
    metrics: dict[str, Any]
    _type: str
    # FIXME: conflict here with ItemSchema
    # operation: str | None = None
    es_highlight: dict[str, Any] | None = None
    target_regions: list[TargetRegion] | None = None
    target_types: list[TargetType] | None = None
    target_subscribers: list | None = None
    scope: str


class ArchiveResourceModel(ItemSchema, MetadataResource):
    pass
