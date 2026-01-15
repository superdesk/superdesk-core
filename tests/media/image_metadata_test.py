import io

from pytest import fixture
from PIL import Image
from PIL.IptcImagePlugin import getiptcinfo
from superdesk.media.image import (
    read_metadata,
    write_metadata,
)
from superdesk.media.metadata_mapping import MediaMetadata, MediaMetadataMapping
from superdesk.media.metadata import get_metadata_from_item
from superdesk.types import Item

from .. import fixture_path


@fixture
def image_binary() -> bytes:
    image_path = fixture_path("cp.jpg", "media")
    with open(image_path, mode="rb") as f:
        return f.read()


@fixture
def cp_sports_image_binary() -> bytes:
    image_path = fixture_path("cp-sports.jpg", "media")
    with open(image_path, mode="rb") as f:
        return f.read()


def test_picture_metadata_read_write(image_binary) -> None:
    metadata = read_metadata(image_binary)
    assert metadata == MediaMetadata(
        {
            "Description": "The Montreal Police logo is seen on a police car in Montreal on Wednesday, July 8, 2020. THE CANADIAN PRESS/Paul Chiasson",
            "DescriptionWriter": "pch",
            "Headline": "",
            "City": "Montreal",
            "Country": "Canada",
            "CountryCode": "CAN",
            "Creator": ["Paul Chiasson"],
            "CreatorsJobtitle": "stf",
            "JobId": "DPI755",
            "Instructions": "EDS NOTE:A FILE PHOTO",
            "Title": "MORT PIÉTONNE MONTRÉAL 20201014",
            "CopyrightNotice": "",
            "CreditLine": "The Canadian Press",
            "ProvinceState": "PQ",
        }
    )

    updated = MediaMetadata(
        {
            "Description": "description",
            "DescriptionWriter": "description writer",
            "Headline": "headline",
            "City": "city",
            "Country": "country",
            "CountryCode": "FOO",
            "Creator": ["creator"],
            "CreatorsJobtitle": "creators jobtitle",
            "JobId": "jobid",
            "Instructions": "instructions",
            "Title": "title",
            "CopyrightNotice": "notice",
            "CreditLine": "credit",
            "ProvinceState": "state",
        }
    )

    next_image = write_metadata(image_binary, updated)

    metadata = read_metadata(next_image)
    assert metadata == updated

    image = Image.open(io.BytesIO(next_image))
    iptc_info = getiptcinfo(image)
    assert iptc_info is not None
    assert isinstance(iptc_info[(2, 120)], bytes)
    assert iptc_info[(2, 120)].decode() == "description"


def test_get_metadata_from_item() -> None:
    item = Item(
        headline="foo",
        slugline="bar",
        extra={
            "filename": "baz",
        },
    )
    mapping: MediaMetadataMapping = dict(
        headline="Headline",
        slugline="Title",
    )
    mapping["extra.filename"] = "JobId"
    metadata = get_metadata_from_item(item, mapping, "picture")
    assert metadata == MediaMetadata(
        Headline="foo",
        Title="bar",
        JobId="baz",
    )


def test_cp_sports_metadata_write(cp_sports_image_binary) -> None:
    """Test updating metadata in cp-sports.jpg."""
    metadata = read_metadata(cp_sports_image_binary)
    assert metadata["Country"] == "CHN"

    # Update the metadata
    updated = MediaMetadata(
        Country="Canada",
        City="Toronto",
    )

    next_image = write_metadata(cp_sports_image_binary, updated)

    # Read back and verify the changes
    metadata = read_metadata(next_image)
    assert metadata["Country"] == "Canada"
    assert metadata["City"] == "Toronto"


def test_cp_sports_metadata_normalization(cp_sports_image_binary) -> None:
    """Test that exiftool fallback metadata is normalized to image module field names."""
    # Read metadata using exiftool fallback (since cp-sports.jpg triggers the fallback)
    metadata = read_metadata(cp_sports_image_binary)

    # Verify that video module field names are NOT present (should be normalized to image module names)
    assert "CaptionWriter" not in metadata  # Should be normalized to DescriptionWriter
    assert "TransmissionReference" not in metadata  # Should be normalized to JobId
    assert "AuthorsPosition" not in metadata  # Should be normalized to CreatorsJobtitle
    assert "Rights" not in metadata  # Should be normalized to CopyrightNotice
    assert "State" not in metadata  # Should be normalized to ProvinceState
    assert "Credit" not in metadata  # Should be normalized to CreditLine

    # Verify actual metadata values with image module field names
    assert metadata.get("DescriptionWriter") == "AW"
    assert metadata.get("JobId") == "RJB101_2022030616"
    assert metadata.get("CreatorsJobtitle") == "STF"
    assert metadata.get("CopyrightNotice") == "Copyright 2022 The Associated Press. All rights reserved"
    assert metadata.get("CreditLine") == "THE CANADIAN PRESS"


def test_metadata_field_mapping_consistency(cp_sports_image_binary) -> None:
    """Test that metadata field mapping denormalization works correctly in write_metadata fallback."""
    # Create metadata with image module field names
    metadata_to_write = MediaMetadata(
        Country="Canada",
        City="Toronto",
        DescriptionWriter="updated_writer",
        JobId="updated_job_123",
        CreatorsJobtitle="updated_photographer",
        CopyrightNotice="Updated Copyright",
        CreditLine="Updated Credit",
        ProvinceState="ON",
    )

    # Use cp-sports.jpg which triggers the exiftool fallback for both read and write
    # This tests that denormalization works correctly in the fallback path
    updated_image = write_metadata(cp_sports_image_binary, metadata_to_write)

    # Read it back
    read_back = read_metadata(updated_image)

    # Verify the mapped fields were written and read back correctly through the fallback
    assert read_back.get("Country") == "Canada"
    assert read_back.get("City") == "Toronto"
    assert read_back.get("DescriptionWriter") == "updated_writer"
    assert read_back.get("JobId") == "updated_job_123"
    assert read_back.get("CreatorsJobtitle") == "updated_photographer"
    assert read_back.get("CopyrightNotice") == "Updated Copyright"
    assert read_back.get("CreditLine") == "Updated Credit"
    assert read_back.get("ProvinceState") == "ON"
