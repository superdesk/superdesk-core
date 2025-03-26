from enum import Enum, unique


@unique
class DeskTypeEnum(str, Enum):
    AUTHORING = "authoring"
    PRODUCTION = "production"


@unique
class MonitoringTypeEnum(str, Enum):
    SEARCH = "search"
    STAGE = "stage"
    SCHEDULED_DESK_OUTPUT = "scheduled_desk_output"
    DESK_OUTPUT = "desk_output"
    PERSONAL = "personal"
    SENT_DESK_OUTPUT = "sent_desk_output"


@unique
class MonitoringViewEnum(str, Enum):
    BLANK = ""
    LIST = "list"
    SWIMLANE = "swimlane"
    PHOTOGRID = "photogrid"


@unique
class UserTypeEnum(str, Enum):
    USER = "user"
    ADMINISTRATOR = "administrator"
    EXTERNAL = "external"


@unique
class PublishState(str, Enum):
    PENDING = "pending"
    PUSHED = "pushed"  #: Item is being pushed with ``publish:push``.
    IN_PROGRESS = "in_progress"
    QUEUED = "queued"
    QUEUED_NOT_TRANSMITTED = "queued_not_transmitted"
    ERROR = "error"  #: Something went wrong.


@unique
class ContentState(str, Enum):
    DRAFT = "draft"
    INGESTED = "ingested"
    ROUTED = "routed"
    FETCHED = "fetched"
    SUBMITTED = "submitted"
    PROGRESS = "in_progress"
    SPIKED = "spiked"
    PUBLISHED = "published"
    KILLED = "killed"
    CORRECTED = "corrected"
    SCHEDULED = "scheduled"
    RECALLED = "recalled"
    UNPUBLISHED = "unpublished"
    CORRECTION = "correction"
    BEING_CORRECTED = "being_corrected"


@unique
class ContentType(str, Enum):
    TEXT = "text"
    PREFORMATTED = "preformatted"
    AUDIO = "audio"
    VIDEO = "video"
    PICTURE = "picture"
    GRAPHIC = "graphic"
    COMPOSITE = "composite"
    EVENT = "event"
    PLANNING = "planning"
    FEATURED_PLANNING = "planning_featured"


TEXT_TYPES = (ContentType.TEXT, ContentType.PREFORMATTED)
MEDIA_TYPES = (ContentType.AUDIO, ContentType.VIDEO, ContentType.PICTURE, ContentType.GRAPHIC)
AUTHORING_TYPES = TEXT_TYPES + MEDIA_TYPES + (ContentType.COMPOSITE,)
