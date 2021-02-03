# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


# codes extracted from IPTC IIM v4.2 specifications


class TAG:
    RECORD_VERSION = "Record Version"
    OBJECT_TYPE_REFERENCE = "Object Type Reference"
    OBJECT_ATTRIBUTE_REFERENCE = "Object Attribute Reference"
    OBJECT_NAME = "Object Name"
    EDIT_STATUS = "Edit Status"
    EDITORIAL_UPDATE = "Editorial Update"
    URGENCY = "Urgency"
    SUBJECT_REFERENCE = "Subject Reference"
    CATEGORY = "Category"
    SUPPLEMENTAL_CATEGORY = "Supplemental Category"
    FIXTURE_IDENTIFIER = "Fixture Identifier"
    KEYWORDS = "Keywords"
    CONTENT_LOCATION_CODE = "Content Location Code"
    CONTENT_LOCATION_NAME = "Content Location Name"
    RELEASE_DATE = "Release Date"
    RELEASE_TIME = "Release Time"
    EXPIRATION_DATE = "Expiration Date"
    EXPIRATION_TIME = "Expiration Time"
    SPECIAL_INSTRUCTIONS = "Special Instructions"
    ACTION_ADVISED = "Action Advised"
    REFERENCE_SERVICE = "Reference Service"
    REFERENCE_DATE = "Reference Date"
    REFERENCE_NUMBER = "Reference Number"
    DATE_CREATED = "Date Created"
    TIME_CREATED = "Time Created"
    DIGITAL_CREATION_DATE = "Digital Creation Date"
    DIGITAL_CREATION_TIME = "Digital Creation Time"
    ORIGINATING_PROGRAM = "Originating Program"
    PROGRAM_VERSION = "Program Version"
    OBJECT_CYCLE = "Object Cycle"
    BY_LINE = "By-line"
    BY_LINE_TITLE = "By-line Title"
    CITY = "City"
    SUBLOCATION = "Sublocation"
    PROVINCE_STATE = "Province/State"
    COUNTRY_PRIMARY_LOCATION_CODE = "Country/Primary Location Code"
    COUNTRY_PRIMARY_LOCATION_NAME = "Country/Primary Location Name"
    ORIGINAL_TRANSMISSION_REFERENCE = "Original Transmission Reference"
    HEADLINE = "Headline"
    CREDIT = "Credit"
    SOURCE = "Source"
    COPYRIGHT_NOTICE = "Copyright Notice"
    CONTACT = "Contact"
    CAPTION_ABSTRACT = "Caption/Abstract"
    WRITER_EDITOR = "Writer/Editor"
    RASTERIZED_CAPTION = "Rasterized Caption"
    IMAGE_TYPE = "Image Type"
    IMAGE_ORIENTATION = "Image Orientation"
    LANGUAGE_IDENTIFIER = "Language Identifier"
    AUDIO_TYPE = "Audio Type"
    AUDIO_SAMPLING_RATE = "Audio Sampling Rate"
    AUDIO_SAMPLING_RESOLUTION = "Audio Sampling Resolution"
    AUDIO_DURATION = "Audio Duration"
    AUDIO_OUTCUE = "Audio Outcue"
    OBJECTDATA_PREVIEW_FILE_FORMAT = "ObjectData Preview File Format"
    OBJECTDATA_PREVIEW_FILE_FORMAT_VERSION = "ObjectData Preview File Format Version"
    OBJECTDATA_PREVIEW_DATA = "ObjectData Preview Data"


iim_codes = {
    (2, 0): TAG.RECORD_VERSION,
    (2, 3): TAG.OBJECT_TYPE_REFERENCE,
    (2, 4): TAG.OBJECT_ATTRIBUTE_REFERENCE,
    (2, 5): TAG.OBJECT_NAME,
    (2, 7): TAG.EDIT_STATUS,
    (2, 8): TAG.EDITORIAL_UPDATE,
    (2, 10): TAG.URGENCY,
    (2, 12): TAG.SUBJECT_REFERENCE,
    (2, 15): TAG.CATEGORY,
    (2, 20): TAG.SUPPLEMENTAL_CATEGORY,
    (2, 22): TAG.FIXTURE_IDENTIFIER,
    (2, 25): TAG.KEYWORDS,
    (2, 26): TAG.CONTENT_LOCATION_CODE,
    (2, 27): TAG.CONTENT_LOCATION_NAME,
    (2, 30): TAG.RELEASE_DATE,
    (2, 35): TAG.RELEASE_TIME,
    (2, 37): TAG.EXPIRATION_DATE,
    (2, 38): TAG.EXPIRATION_TIME,
    (2, 40): TAG.SPECIAL_INSTRUCTIONS,
    (2, 42): TAG.ACTION_ADVISED,
    (2, 45): TAG.REFERENCE_SERVICE,
    (2, 47): TAG.REFERENCE_DATE,
    (2, 50): TAG.REFERENCE_NUMBER,
    (2, 55): TAG.DATE_CREATED,
    (2, 60): TAG.TIME_CREATED,
    (2, 62): TAG.DIGITAL_CREATION_DATE,
    (2, 63): TAG.DIGITAL_CREATION_TIME,
    (2, 65): TAG.ORIGINATING_PROGRAM,
    (2, 70): TAG.PROGRAM_VERSION,
    (2, 75): TAG.OBJECT_CYCLE,
    (2, 80): TAG.BY_LINE,
    (2, 85): TAG.BY_LINE_TITLE,
    (2, 90): TAG.CITY,
    (2, 92): TAG.SUBLOCATION,
    (2, 95): TAG.PROVINCE_STATE,
    (2, 100): TAG.COUNTRY_PRIMARY_LOCATION_CODE,
    (2, 101): TAG.COUNTRY_PRIMARY_LOCATION_NAME,
    (2, 103): TAG.ORIGINAL_TRANSMISSION_REFERENCE,
    (2, 105): TAG.HEADLINE,
    (2, 110): TAG.CREDIT,
    (2, 115): TAG.SOURCE,
    (2, 116): TAG.COPYRIGHT_NOTICE,
    (2, 118): TAG.CONTACT,
    (2, 120): TAG.CAPTION_ABSTRACT,
    (2, 122): TAG.WRITER_EDITOR,
    (2, 125): TAG.RASTERIZED_CAPTION,
    (2, 130): TAG.IMAGE_TYPE,
    (2, 131): TAG.IMAGE_ORIENTATION,
    (2, 135): TAG.LANGUAGE_IDENTIFIER,
    (2, 150): TAG.AUDIO_TYPE,
    (2, 151): TAG.AUDIO_SAMPLING_RATE,
    (2, 152): TAG.AUDIO_SAMPLING_RESOLUTION,
    (2, 153): TAG.AUDIO_DURATION,
    (2, 154): TAG.AUDIO_OUTCUE,
    (2, 200): TAG.OBJECTDATA_PREVIEW_FILE_FORMAT,
    (2, 201): TAG.OBJECTDATA_PREVIEW_FILE_FORMAT_VERSION,
    (2, 202): TAG.OBJECTDATA_PREVIEW_DATA,
}
