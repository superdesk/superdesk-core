# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import NamedTuple
from copy import deepcopy

from superdesk.resource import Resource, not_analyzed, not_indexed, not_enabled, text_with_keyword
from .packages import LINKED_IN_PACKAGES, PACKAGE
from eve.utils import config
from superdesk.utils import SuperdeskBaseEnum

GUID_TAG = "tag"
GUID_FIELD = "guid"
GUID_NEWSML = "newsml"
INGEST_ID = "ingest_id"
INGEST_VERSION = "ingest_version"
FAMILY_ID = "family_id"
ASSOCIATIONS = "associations"


#: item public states
class PubStatuses(NamedTuple):
    USABLE: str
    HOLD: str
    CANCELED: str


PUB_STATUS: PubStatuses = PubStatuses("usable", "withheld", "canceled")


class ContentTypes(NamedTuple):
    TEXT: str
    PREFORMATTED: str
    AUDIO: str
    VIDEO: str
    PICTURE: str
    GRAPHIC: str
    COMPOSITE: str
    EVENT: str


CONTENT_TYPE: ContentTypes = ContentTypes(
    "text", "preformatted", "audio", "video", "picture", "graphic", "composite", "event"
)

MEDIA_TYPES = ("audio", "video", "picture", "graphic")
ITEM_TYPE = "type"
ITEM_STATE = "state"
ITEM_PRIORITY = "priority"
ITEM_URGENCY = "urgency"


#: item internal states
class ContentStates(NamedTuple):
    DRAFT: str
    INGESTED: str
    ROUTED: str
    FETCHED: str
    SUBMITTED: str
    PROGRESS: str
    SPIKED: str
    PUBLISHED: str
    KILLED: str
    CORRECTED: str
    SCHEDULED: str
    RECALLED: str
    UNPUBLISHED: str
    CORRECTION: str
    BEING_CORRECTED: str


CONTENT_STATE: ContentStates = ContentStates(
    "draft",
    "ingested",
    "routed",
    "fetched",
    "submitted",
    "in_progress",
    "spiked",
    "published",
    "killed",
    "corrected",
    "scheduled",
    "recalled",
    "unpublished",
    "correction",
    "being_corrected",
)

PUBLISH_STATES = {
    CONTENT_STATE.PUBLISHED,
    CONTENT_STATE.SCHEDULED,
    CONTENT_STATE.CORRECTED,
    CONTENT_STATE.KILLED,
    CONTENT_STATE.RECALLED,
    CONTENT_STATE.UNPUBLISHED,
    CONTENT_STATE.BEING_CORRECTED,
}


class Formats(NamedTuple):
    HTML: str
    PRESERVED: str


FORMAT = "format"
FORMATS: Formats = Formats("HTML", "preserved")

BYLINE = "byline"
SIGN_OFF = "sign_off"
EMBARGO = "embargo"
PUBLISH_SCHEDULE = "publish_schedule"
SCHEDULE_SETTINGS = "schedule_settings"
PROCESSED_FROM = "processed_from"

# part the task dict
LAST_DESK = "last_desk"
LAST_AUTHORING_DESK = "last_authoring_desk"
LAST_PRODUCTION_DESK = "last_production_desk"
DESK_HISTORY = "desk_history"

ITEM_EVENT_ID = "event_id"

geopoint = {
    "type": "dict",
    "mapping": {"type": "geo_point"},
    "nullable": True,
    "schema": {
        "lat": {"type": "float"},
        "lon": {"type": "float"},
    },
}

entity_metadata = {
    "type": "list",
    "nullable": True,
    "mapping": {
        "type": "object",
        "dynamic": False,
        "properties": {
            "name": text_with_keyword,
            "qcode": not_analyzed,
            "scheme": not_analyzed,
            "source": not_analyzed,
        },
    },
}

metadata_schema = {
    config.ID_FIELD: {"type": "string", "unique": True},
    #: Identifiers
    "guid": {"type": "string", "unique": True, "mapping": not_analyzed},
    "uri": {
        "type": "string",
        "mapping": not_analyzed,
    },
    "unique_id": {
        "type": "integer",
        "unique": True,
    },
    "unique_name": {"type": "string", "unique": True, "mapping": not_analyzed},
    "version": {"type": "integer"},
    "ingest_id": {"type": "string", "mapping": not_analyzed},
    "ingest_version": {"type": "string", "mapping": not_analyzed},
    "family_id": {"type": "string", "mapping": not_analyzed},
    "related_to": {  # this field keeps a reference to the related item from which metadata has been copied
        "type": "string",
        "mapping": not_analyzed,
    },
    # Audit Information
    "original_creator": Resource.rel("users"),
    "version_creator": Resource.rel("users"),
    "firstcreated": {"type": "datetime"},
    "versioncreated": {"type": "datetime"},
    "firstpublished": {
        "type": "datetime",
        "required": False,
        "nullable": True,
    },
    # Ingest Details
    "ingest_provider": Resource.rel("ingest_providers"),
    "source": {"type": "string", "mapping": not_analyzed},  # The value is copied from the ingest_providers vocabulary
    "original_source": {"type": "string", "mapping": not_analyzed},  # This value is extracted from the ingest
    "ingest_provider_sequence": {"type": "string", "mapping": not_analyzed},
    # Copyright Information
    "usageterms": {
        "type": "string",
        "nullable": True,
    },
    "copyrightnotice": {"type": "string", "nullable": True, "mapping": not_indexed},
    "copyrightholder": {"type": "string", "nullable": True},
    # Category Details
    "anpa_category": {
        "type": "list",
        "nullable": True,
        "mapping": {
            "type": "object",
            "properties": {
                "qcode": not_analyzed,
                "name": not_analyzed,
            },
        },
    },
    "subject": {
        "type": "list",
        "mapping": {"type": "object", "dynamic": False, "properties": {"qcode": not_analyzed, "name": not_analyzed}},
    },
    "genre": {
        "type": "list",
        "nullable": True,
        "mapping": {"type": "object", "properties": {"name": not_analyzed, "qcode": not_analyzed}},
    },
    "company_codes": {
        "type": "list",
        "mapping": {
            "type": "object",
            "properties": {"qcode": not_analyzed, "name": not_analyzed, "security_exchange": not_analyzed},
        },
    },
    # Item Metadata
    ITEM_TYPE: {
        "type": "string",
        "allowed": tuple(CONTENT_TYPE),
        "default": "text",
        "mapping": not_analyzed,
    },
    "package_type": {"type": "string", "allowed": ["takes"]},  # deprecated
    "language": {
        "type": "string",
        "mapping": not_analyzed,
        "nullable": True,
    },
    "abstract": {
        "type": "string",
        "nullable": True,
    },
    "headline": {"type": "string"},
    "slugline": {
        "type": "string",
        "mapping": {
            "type": "string",
            "fielddata": True,
            "fields": {
                "phrase": {
                    "type": "string",
                    "analyzer": "phrase_prefix_analyzer",
                    "search_analyzer": "phrase_prefix_analyzer",
                    "fielddata": True,
                }
            },
        },
    },
    "anpa_take_key": {
        "type": "string",
        "nullable": True,
    },
    "correction_sequence": {"type": "integer", "nullable": True, "mapping": not_analyzed},
    "rewrite_sequence": {"type": "integer", "nullable": True, "mapping": not_analyzed},
    "rewrite_of": {
        "type": "string",
        "nullable": True,
        "mapping": not_analyzed,
    },
    "rewritten_by": {
        "type": "string",
        "nullable": True,
        "mapping": not_analyzed,
    },
    "sequence": {
        "type": "integer",
        "nullable": True,
    },
    "keywords": {"type": "list", "mapping": {"type": "string"}},
    "word_count": {"type": "integer"},
    "priority": {"type": "integer", "nullable": True},
    "urgency": {"type": "integer", "nullable": True},
    "profile": {
        "type": "string",
        "nullable": True,
        "mapping": not_analyzed,
    },
    # Related to state of an article
    ITEM_STATE: {
        "type": "string",
        "allowed": tuple(CONTENT_STATE),
        "mapping": not_analyzed,
    },
    # The previous state the item was in before for example being spiked, when un-spiked it will revert to this state
    "revert_state": {
        "type": "string",
        "allowed": tuple(CONTENT_STATE),
        "mapping": not_analyzed,
    },
    "pubstatus": {
        "type": "string",
        "allowed": tuple(PUB_STATUS),
        "default": PUB_STATUS.USABLE,
        "mapping": not_analyzed,
        "nullable": True,
    },
    "signal": {
        "type": "list",
        "mapping": {
            "type": "object",
            "properties": {"qcode": not_analyzed, "name": not_analyzed, "scheme": not_analyzed},
        },
    },
    BYLINE: {
        "type": "string",
        "nullable": True,
    },
    "ednote": {
        "type": "string",
        "nullable": True,
    },
    "authors": {
        "type": "list",
        "nullable": True,
        "mapping": {
            "type": "object",
            "dynamic": False,
            "properties": {
                "uri": not_analyzed,
                "parent": not_analyzed,
                "name": not_analyzed,
                "role": not_analyzed,
                "jobtitle": not_enabled,
            },
        },
    },
    "description_text": {"type": "string", "nullable": True},
    # This is a description of the item as recieved from its source.
    "archive_description": {"type": "string", "nullable": True},
    "groups": {
        "type": "list",
        "minlength": 1,
        "nullable": True,
        "mapping": {
            "dynamic": False,
            "properties": {
                "id": not_analyzed,
                "refs": {
                    "dynamic": False,
                    "properties": {
                        "idRef": not_analyzed,
                        "_id": not_analyzed,
                        "uri": not_analyzed,
                        "guid": not_analyzed,
                        "type": not_analyzed,
                        "location": not_analyzed,
                        "headline": {"type": "string"},
                        "slugline": {"type": "string"},
                    },
                },
            },
        },
    },
    "deleted_groups": {
        "type": "list",
        "minlength": 1,
        "nullable": True,
    },
    "body_html": {
        "type": "string",
        "nullable": True,
        "mapping": {"type": "string", "analyzer": "html_field_analyzer", "search_analyzer": "standard"},
    },
    "body_text": {
        "type": "string",
        "nullable": True,
    },
    "dateline": {
        "type": "dict",
        "nullable": True,
        "schema": {
            "located": {
                "type": "dict",
                "nullable": True,
                "schema": {
                    "state_code": {"type": "string"},
                    "city": {"type": "string"},
                    "tz": {"type": "string"},
                    "country_code": {"type": "string"},
                    "dateline": {"type": "string"},
                    "alt_name": {"type": "string"},
                    "state": {"type": "string"},
                    "city_code": {"type": "string"},
                    "country": {"type": "string"},
                    "code": {"type": "string"},
                    "scheme": {"type": "string"},
                    "location": geopoint,
                    "place": {
                        "type": "dict",
                        "nullable": True,
                        "mapping": not_enabled,
                        "schema": {
                            "code": {"type": "string"},
                            "name": {"type": "string"},
                            "qcode": {"type": "string"},
                            "scheme": {"type": "string"},
                            "feature_class": {"type": "string"},
                            "location": geopoint,
                            "continent_code": {"type": "string", "nullable": True},
                            "region": {"type": "string", "nullable": True},
                            "region_code": {"type": "string", "nullable": True},
                            "locality": {"type": "string", "nullable": True},
                            "state": {"type": "string", "nullable": True},
                            "country": {"type": "string", "nullable": True},
                            "world_region": {"type": "string", "nullable": True},
                            "locality_code": {"type": "string", "nullable": True},
                            "state_code": {"type": "string", "nullable": True},
                            "country_code": {"type": "string", "nullable": True},
                            "world_region_code": {"type": "string", "nullable": True},
                            "rel": {"type": "string", "nullable": True},
                            "tz": {"type": "string", "nullable": True},
                        },
                    },
                },
            },
            "date": {"type": "datetime", "nullable": True},
            "source": {"type": "string"},
            "text": {"type": "string", "nullable": True},
        },
    },
    "expiry": {"type": "datetime"},
    # Media Related
    "media": {"type": "file"},
    "mimetype": {"type": "string", "mapping": not_analyzed},
    "poi": {
        "type": "dict",
        "schema": {"x": {"type": "float", "nullable": False}, "y": {"type": "float", "nullable": False}},
    },
    "renditions": {
        "type": "dict",
        "schema": {},
        "allow_unknown": True,
        "mapping": not_enabled,
    },
    "filemeta": {
        "type": "dict",
        "schema": {},
        "allow_unknown": True,
        "mapping": not_enabled,
    },
    "filemeta_json": {"type": "string"},
    "media_file": {"type": "string"},
    "contents": {"type": "list"},
    ASSOCIATIONS: {
        "type": "dict",
        "allow_unknown": True,
        "schema": {},
        "mapping": {
            "type": "object",
            "dynamic": False,
            "properties": {
                "featuremedia": {  # keep indexing featuremedia - we do some filtering using it
                    "type": "object",
                    "dynamic": False,
                    "properties": {
                        "_id": not_analyzed,
                        "guid": not_analyzed,
                        "unique_id": {"type": "integer"},
                    },
                }
            },
        },
    },
    # track references to other objects,
    # based on associations but allows queries
    "refs": {
        "type": "list",
        "readonly": True,
        "schema": {
            "_id": {"type": "string"},
            "key": {"type": "string"},
            "uri": {"type": "string"},
            "guid": {"type": "string"},
            "type": {"type": "string"},
        },
        "mapping": {
            "type": "object",
            "properties": {
                "_id": not_analyzed,
                "key": not_analyzed,
                "uri": not_analyzed,
                "guid": not_analyzed,
                "type": not_analyzed,
            },
        },
    },
    "alt_text": {"type": "string", "nullable": True},
    # aka Locator as per NewML Specification
    "place": {
        "type": "list",
        "nullable": True,
        "mapping": {
            "type": "object",
            "dynamic": False,
            "properties": {
                "scheme": not_analyzed,
                "qcode": not_analyzed,
                "code": not_analyzed,  # content api
                "name": not_analyzed,
                "locality": not_analyzed,  # can be used for city/town/village etc.
                "state": not_analyzed,
                "country": not_analyzed,
                "world_region": not_analyzed,
                "locality_code": not_analyzed,
                "state_code": not_analyzed,
                "country_code": not_analyzed,
                "world_region_code": not_analyzed,
                "feature_class": not_analyzed,
                "location": {"type": "geo_point"},
                "rel": not_analyzed,
            },
        },
    },
    "event": deepcopy(entity_metadata),
    "person": deepcopy(entity_metadata),
    "object": deepcopy(entity_metadata),
    "organisation": deepcopy(entity_metadata),
    # Not Categorized
    "creditline": {"type": "string"},
    LINKED_IN_PACKAGES: {
        "type": "list",
        "readonly": True,
        "schema": {
            "type": "dict",
            "schema": {PACKAGE: Resource.rel("archive"), "package_type": {"type": "string"}},  # deprecated
        },
    },
    "highlight": Resource.rel("highlights"),
    "highlights": {"type": "list", "schema": Resource.rel("highlights", True)},
    "marked_desks": {
        "type": "list",
        "nullable": True,
        "schema": {
            "type": "dict",
            "schema": {
                "desk_id": Resource.rel("desks", True),
                "date_marked": {"type": "datetime", "nullable": True},
                "user_marked": Resource.rel("users", required=False, nullable=True),
                "date_acknowledged": {"type": "datetime", "nullable": True},
                "user_acknowledged": Resource.rel("users", required=False, nullable=True),
            },
        },
    },
    "more_coming": {"type": "boolean"},  # deprecated
    # Field which contains all the sign-offs done on this article, eg. twd/jwt/ets
    SIGN_OFF: {
        "type": "string",
        "nullable": True,
    },
    # Desk and Stage Details
    "task": {
        "type": "dict",
        "schema": {
            "user": {"type": "string", "mapping": not_analyzed, "nullable": True},
            "desk": {"type": "string", "mapping": not_analyzed, "nullable": True},
            "desk_history": {"type": "list", "mapping": not_analyzed},
            "last_desk": {"type": "string", "mapping": not_analyzed},
            "stage": {"type": "string", "mapping": not_analyzed, "nullable": True},
            "status": {"type": "string", "mapping": not_analyzed},
        },
    },
    # Task and Lock Details
    "task_id": {"type": "string", "mapping": not_analyzed, "versioned": False},
    "lock_user": Resource.rel("users"),
    "lock_time": {"type": "datetime", "versioned": False},
    "lock_session": Resource.rel("auth"),
    # Action when the story is locked: edit, correct, kill
    "lock_action": {"type": "string", "mapping": not_analyzed, "nullable": True},
    # template used to create an item
    "template": Resource.rel("content_templates"),
    "body_footer": {  # Public Service Announcements
        "type": "string",
        "nullable": True,
        "mapping": not_indexed,
    },
    "flags": {
        "type": "dict",
        "schema": {
            "marked_for_not_publication": {"type": "boolean", "default": False},
            "marked_for_legal": {"type": "boolean", "default": False},
            "marked_archived_only": {"type": "boolean", "default": False},
            "marked_for_sms": {"type": "boolean", "default": False},
        },
        "default": {
            "marked_for_not_publication": False,
            "marked_for_legal": False,
            "marked_archived_only": False,
            "marked_for_sms": False,
        },
    },
    "sms_message": {"type": "string", "mapping": not_analyzed, "nullable": True},
    FORMAT: {"type": "string", "mapping": not_analyzed, "default": FORMATS.HTML},
    # True indicates that the item has been or is to be published as a result of a routing rule
    "auto_publish": {"type": "boolean"},
    # draft-js internal data
    "fields_meta": {
        "type": "dict",
        "schema": {},
        "allow_unknown": True,
        "nullable": True,
        "mapping": not_enabled,
    },
    "annotations": {
        "type": "list",
        "mapping": not_enabled,
        "schema": {
            "type": "dict",
            "schema": {
                "id": {"type": "integer"},
                "type": {"type": "string"},
                "body": {"type": "string"},
            },
        },
    },
    "extra": {
        "type": "dict",
        "schema": {},
        "mapping": not_enabled,
        "allow_unknown": True,
    },
    "attachments": {
        "type": "list",
        "nullable": True,
        "schema": {
            "type": "dict",
            "schema": {
                "attachment": Resource.rel("attachments", nullable=False),
            },
        },
    },
    # references assignment related to the coverage
    "assignment_id": {"type": "string", "mapping": not_analyzed},
    "translated_from": {
        "type": "string",
        "mapping": not_analyzed,
    },
    "translation_id": {
        "type": "string",
        "mapping": not_analyzed,
    },
    "translations": {
        "type": "list",
        "mapping": not_analyzed,
    },
    # references item id for items auto published using internal destinations
    PROCESSED_FROM: {"type": "string", "mapping": not_analyzed},
    # ingested embargoed info, not using embargo to avoid validation
    "embargoed": {"type": "datetime"},
    "embargoed_text": {"type": "string", "mapping": not_indexed},
    "marked_for_user": Resource.rel("users", required=False, nullable=True),
    "broadcast": {
        "type": "dict",
        "schema": {
            "status": {"type": "string", "mapping": not_analyzed},
            "master_id": {"type": "string", "mapping": not_analyzed},
            "rewrite_id": {"type": "string", "mapping": not_analyzed},
        },
    },
    ITEM_EVENT_ID: {"type": "string", "mapping": not_analyzed},
    # schedules
    EMBARGO: {"type": "datetime", "nullable": True},
    PUBLISH_SCHEDULE: {"type": "datetime", "nullable": True},
    SCHEDULE_SETTINGS: {
        "type": "dict",
        "schema": {
            "time_zone": {"type": "string", "nullable": True, "mapping": not_analyzed},
            "utc_embargo": {"type": "datetime", "nullable": True},
            "utc_publish_schedule": {"type": "datetime", "nullable": True},
        },
    },
    # usage tracking
    "used": {"type": "boolean"},
    "used_count": {"type": "integer"},
    "used_updated": {"type": "datetime"},
    # system fields
    "_type": {"type": "string", "mapping": None},
    "operation": {"type": "string"},
    "es_highlight": {"type": "dict", "allow_unknown": True, "readonly": True},
    # targeting fields
    "target_regions": {
        "type": "list",
        "nullable": True,
        "schema": {
            "type": "dict",
            "schema": {"qcode": {"type": "string"}, "name": {"type": "string"}, "allow": {"type": "boolean"}},
        },
    },
    "target_types": {
        "type": "list",
        "nullable": True,
        "schema": {
            "type": "dict",
            "schema": {"qcode": {"type": "string"}, "name": {"type": "string"}, "allow": {"type": "boolean"}},
        },
    },
    "target_subscribers": {"type": "list", "nullable": True},
}

metadata_schema["lock_user"]["versioned"] = False
metadata_schema["lock_session"]["versioned"] = False

crop_schema = {
    "CropLeft": {"type": "integer"},
    "CropRight": {"type": "integer"},
    "CropTop": {"type": "integer"},
    "CropBottom": {"type": "integer"},
}


def remove_metadata_for_publish(item):
    """Remove metadata from item that should not be public.

    :param item: Item containing the metadata
    :return: item
    """
    from superdesk.attachments import is_attachment_public

    if len(item.get("attachments", [])) > 0:
        item["attachments"] = [attachment for attachment in item["attachments"] if is_attachment_public(attachment)]

    return item


class Priority(SuperdeskBaseEnum):
    """Priority values."""

    Flash = 1
    Urgent = 2
    Three_Paragraph = 3
    Screen_Finance = 4
    Continuous_News = 5
    Ordinary = 6


def get_schema(versioning=False):
    schema = metadata_schema.copy()

    if versioning:
        schema.update(
            {
                "_id_document": {"type": "string"},
                "_current_version": {"type": "integer"},
            }
        )

    return schema
