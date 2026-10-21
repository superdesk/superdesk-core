from io import BytesIO
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import pytest
from exiftool import ExifToolHelper

from apps.archive.upload_staging_processing import PICTURE_XMP_TAGS, extract_staged_metadata, read_staged_metadata
from superdesk.media.metadata import read_metadata
from tests import fixture_path


def test_iptc_hook_metadata_preserves_tags_and_list_values():
    raw = {
        "IPTC:ObjectName": "IPTC slugline",
        "XMP:Title": "XMP slugline",
        "IPTC:SubjectReference": ["01000000", "02000000"],
        "IPTC:Category": "S",
        "IPTC:SupplementalCategories": ["SPORT", "NEWS"],
        "IPTC:LanguageIdentifier": "it",
        "IPTC:Source": "Supplier",
        "IPTC:DateCreated": "2026:10:21",
        "IPTC:TimeCreated": "09:00:00+02:00",
        "IPTC:ReleaseDate": "2026:10:22",
        "IPTC:ReleaseTime": "10:00:00+02:00",
        "IPTC:City": "Rome",
        "XMP:Country": "Italy",
        "XMP:Creator": ["Photographer"],
    }
    with patch("exiftool.ExifToolHelper") as tool:
        tool.return_value.__enter__.return_value.get_metadata.return_value = [raw]
        canonical, metadata = read_staged_metadata("/tmp/photo.jpg", "image")
        tool.return_value.__enter__.return_value.get_metadata.assert_called_once_with(
            "/tmp/photo.jpg", ["-G", "-xmp:all", "-iptc:all"]
        )
    assert canonical["Title"] == "XMP slugline"
    assert canonical["Creator"] == ["Photographer"]
    assert metadata == {
        "ObjectName": "IPTC slugline",
        "SubjectReference": ["01000000", "02000000"],
        "Category": "S",
        "SupplementalCategories": ["SPORT", "NEWS"],
        "LanguageIdentifier": "it",
        "Source": "Supplier",
        "DateCreated": "2026:10:21",
        "TimeCreated": "09:00:00+02:00",
        "ReleaseDate": "2026:10:22",
        "ReleaseTime": "10:00:00+02:00",
        "City": "Rome",
        "Country-PrimaryLocationName": "Italy",
        "By-line": ["Photographer"],
    }


@pytest.mark.parametrize("content_type", ["image", "video"])
def test_xmp_hook_aliases_and_creation_time(content_type):
    raw = {
        "XMP:DateCreated": "2026:10:21 09:00:00+02:00",
        "XMP:SubjectCode": ["01000000"],
        "XMP:State": "Ontario",
        "XMP:Rights": "Copyright",
        "XMP:CaptionWriter": "Editor",
        "XMP:Instructions": "Note",
        "XMP:TransmissionReference": "filename",
        "IPTC:ObjectName": "",
        "XMP:Title": "XMP title",
    }
    with patch("exiftool.ExifToolHelper") as tool:
        tool.return_value.__enter__.return_value.get_metadata.return_value = [raw]
        _, metadata = read_staged_metadata("/tmp/media", content_type)
    assert metadata == {
        "DateCreated": "2026:10:21 09:00:00+02:00",
        "TimeCreated": "09:00:00+02:00",
        "SubjectReference": ["01000000"],
        "Province-State": "Ontario",
        "CopyrightNotice": "Copyright",
        "Writer-Editor": "Editor",
        "SpecialInstructions": "Note",
        "OriginalTransmissionReference": "filename",
        "ObjectName": "XMP title",
    }


def test_hook_metadata_from_real_picture():
    with open(fixture_path("cp.jpg", "media"), "rb") as source, NamedTemporaryFile(suffix=".jpg") as photo:
        photo.write(source.read())
        photo.flush()
        with ExifToolHelper() as tool:
            tool.execute(
                "-IPTC:SubjectReference=01000000",
                "-IPTC:Category=S",
                "-XMP:Language=it",
                "-IPTC:DateCreated=2026:10:21",
                "-IPTC:TimeCreated=09:00:00+02:00",
                "-overwrite_original",
                photo.name,
            )
        canonical, metadata = read_staged_metadata(photo.name, "image")
        assert canonical == dict(read_metadata(photo.name, "picture"))
    assert metadata["By-line"] == "Paul Chiasson"
    assert metadata["City"] == "Montreal"
    assert metadata["Country-PrimaryLocationName"] == "Canada"
    assert metadata["ObjectName"]
    assert metadata["SubjectReference"] == "01000000"
    assert metadata["Category"] == "S"
    assert metadata["LanguageIdentifier"] == "it"
    assert metadata["DateCreated"] == "2026:10:21"
    assert metadata["TimeCreated"] == "09:00:00+02:00"


@pytest.mark.asyncio
@pytest.mark.parametrize("file_type", ["image", "video"])
async def test_staged_extraction_reads_once_for_both_payloads(file_type):
    raw = {"XMP:Title": "Canonical", "XMP:Creator": "Photographer", "IPTC:ObjectName": "IPTC", "IPTC:Category": "S"}
    with (
        patch("exiftool.ExifToolHelper") as tool,
        patch("apps.archive.upload_staging_processing.get_app_config", return_value={}),
        patch("apps.archive.upload_staging_processing.process_file", return_value={}),
    ):
        reader = tool.return_value.__enter__.return_value.get_metadata
        reader.return_value = [raw]
        updates = await extract_staged_metadata(
            {"_id": "stage", "mimetype": f"{file_type}/test", "size": 6}, BytesIO(b"binary"), "/tmp/media"
        )
        tool.assert_called_once_with()
        reader.assert_called_once_with("/tmp/media", ["-G", "-xmp:all", "-iptc:all"])
    assert updates["metadata_status"] == "ready"
    assert updates["raw_metadata"]["Title"] == "Canonical"
    assert updates["raw_metadata"]["Creator"] == (["Photographer"] if file_type == "image" else "Photographer")
    assert updates["iptc_metadata"] == {
        "ObjectName": "IPTC" if file_type == "image" else "Canonical",
        "By-line": "Photographer",
        **({"Category": "S"} if file_type == "image" else {}),
    }
    assert updates["meta"]["byline"] == "Photographer"


@pytest.mark.parametrize("filename", ["cp.jpg", "cp-sports.jpg"])
@pytest.mark.parametrize("file_type,content_type", [("image", "picture"), ("video", "video")])
def test_single_extraction_preserves_canonical_metadata(filename, file_type, content_type):
    path = str(fixture_path(filename, "media"))
    canonical, _ = read_staged_metadata(path, file_type)
    previous = dict(read_metadata(path, content_type))
    if file_type == "image":
        # The legacy pyexiv2 fallback returned sparse fields and scalar creators.
        previous = {field: previous.get(field, "") for field in PICTURE_XMP_TAGS}
        creator = previous["Creator"]
        previous["Creator"] = creator if isinstance(creator, list) else [creator] if creator else []
    assert canonical == previous


@pytest.mark.asyncio
async def test_audio_does_not_extract_embedded_metadata():
    with (
        patch("exiftool.ExifToolHelper") as tool,
        patch("apps.archive.upload_staging_processing.get_app_config", return_value={}),
        patch("apps.archive.upload_staging_processing.process_file", return_value={}),
    ):
        updates = await extract_staged_metadata(
            {"_id": "stage", "mimetype": "audio/mpeg", "size": 6}, BytesIO(b"binary"), "/tmp/audio"
        )
    tool.assert_not_called()
    assert updates["raw_metadata"] == {}
    assert updates["iptc_metadata"] == {}
