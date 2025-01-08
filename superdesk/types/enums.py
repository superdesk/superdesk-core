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
