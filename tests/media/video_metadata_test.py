from pytest import fixture
from unittest.mock import patch
from .. import fixture_path


@fixture
def image_binary() -> bytes:
    p = fixture_path("cp.jpg", "media")
    with open(p, mode="rb") as f:
        return f.read()


@fixture
def video_binary() -> bytes:
    p = fixture_path("cp.mov", "media")
    with open(p, mode="rb") as f:
        return f.read()


@fixture
def video_updated_binary() -> bytes:
    p = fixture_path("cp_updated.mov", "media")
    with open(p, mode="rb") as f:
        return f.read()


@patch("tempfile.NamedTemporaryFile")
@patch("exiftool.ExifToolHelper")
def test_read_with_exiftool(et, tempfile, video_binary) -> None:
    from unittest.mock import MagicMock

    tmp = MagicMock()
    tmp.name = "test.mp4"
    tempfile.return_value.__enter__.return_value = tmp
    et_instance = et.return_value.__enter__.return_value
    et_instance.get_metadata.return_value = [{"XMP:Creator": "Phil Harvey"}]

    from superdesk.media.video import read_with_exiftool

    result = read_with_exiftool(video_binary)

    tempfile.assert_called_once_with(delete=True)
    tmp.write.assert_called_once_with(video_binary)
    tmp.flush.assert_called_once()
    et_instance.get_metadata.assert_called_once_with(tmp.name, ["-xmp:all"])
    assert result == {"XMP:Creator": "Phil Harvey"}


@patch("superdesk.media.video.read_with_exiftool")
def test_read_metadata(read_with_exiftool, video_binary) -> None:
    read_with_exiftool.return_value = {"XMP:Creator": "Phil Harvey"}

    from superdesk.media.video import read_metadata

    result = read_metadata(video_binary)

    read_with_exiftool.assert_called_once_with(video_binary)
    assert result == {"Creator": "Phil Harvey"}


def test_map_exiftool_args() -> None:
    from superdesk.media.metadata_mapping import MediaMetadata
    from superdesk.media.video import map_exiftool_args

    video: MediaMetadata = {"Creator": ["Phil", "Harvey"]}
    expected = ["-sep", ",", "-Creator=Phil,Harvey", "-overwrite_original_in_place"]

    assert map_exiftool_args(video) == expected


def test_get_video_from_photo() -> None:
    from superdesk.media.metadata_mapping import MediaMetadata
    from superdesk.media.video import get_video_from_photo

    photo: MediaMetadata = {
        "Description": (
            "The Montreal Police logo is seen on "
            "a police car in Montreal on Wednesday, July 8, 2020. "
            "THE CANADIAN PRESS/Paul Chiasson"
        ),
        "DescriptionWriter": "pch",
        "Headline": "",
        "Instructions": "EDS NOTE:A FILE PHOTO",
        "JobId": "DPI755",
        "Title": "MORT PIÉTONNE MONTRÉAL 20201014",
        "Creator": ["Paul Chiasson"],
        "CreatorsJobtitle": "stf",
        "CopyrightNotice": "",
        "City": "Montreal",
        "Country": "Canada",
        "CountryCode": "CAN",
        "CreditLine": "The Canadian Press",
        "ProvinceState": "PQ",
    }
    expected = {
        "Description": (
            "The Montreal Police logo is seen on "
            "a police car in Montreal on Wednesday, July 8, 2020. "
            "THE CANADIAN PRESS/Paul Chiasson"
        ),
        "CaptionWriter": "pch",
        "City": "Montreal",
        "Country": "Canada",
        "CountryCode": "CAN",
        "Creator": ["Paul Chiasson"],
        "AuthorsPosition": "stf",
        "TransmissionReference": "DPI755",
        "Instructions": "EDS NOTE:A FILE PHOTO",
        "Title": "MORT PIÉTONNE MONTRÉAL 20201014",
        "Credit": "The Canadian Press",
        "State": "PQ",
    }

    assert get_video_from_photo(photo) == expected


@patch("tempfile.NamedTemporaryFile")
@patch("exiftool.ExifToolHelper")
def test_write_with_exiftool(et, tempfile, video_binary, video_updated_binary) -> None:
    from unittest.mock import MagicMock

    tmp = MagicMock()
    tmp.name = "test.mp4"
    tmp.read.return_value = video_updated_binary
    tempfile.return_value.__enter__.return_value = tmp
    et_instance = et.return_value.__enter__.return_value

    from superdesk.media.video import write_with_exiftool

    args = ["-sep", ",", "-Creator=Phil,Harvey", "-overwrite_original_in_place"]
    result = write_with_exiftool(video_binary, args)

    tempfile.assert_called_once()
    tmp.write.assert_called_once_with(video_binary)
    tmp.flush.assert_called_once()
    et_instance.execute.assert_called_once_with(*args, tmp.name)
    assert result == video_updated_binary


def test_read_from_video(video_binary) -> None:
    from superdesk.media.video import read_metadata

    expected = {
        "Description": "Your Description Here",
        "Headline": "Your Headline",
        "City": "Your City",
        "Country": "Your Country",
        "CountryCode": "US",
        "Creator": "Your Creator Name",
        "AuthorsPosition": "Your Job Title",
        "TransmissionReference": "Your Job ID",
        "Instructions": "Your Instructions",
        "Title": "Your Title",
        "Rights": "Your Copyright Notice",
        "Credit": "Your Credit Line",
        "State": "Your Province or State",
        "CaptionWriter": "Your Caption Writer",
    }
    assert read_metadata(video_binary) == expected


def test_write_from_video(video_binary, video_updated_binary) -> None:
    from superdesk.media.metadata_mapping import MediaMetadata
    from superdesk.media.video import write_metadata

    updates: MediaMetadata = {
        "Description": "Your Description Here 1",
        "Headline": "Your Headline 2",
        "City": "Your City 3",
        "Country": "Your Country 4",
        "CountryCode": "US 5",
        "Creator": ["Your Creator Name 6", "Your Creator Name 6"],
        "AuthorsPosition": "Your Job Title 7",
        "TransmissionReference": "Your Job ID 8",
        "Instructions": "Your Instructions 9",
        "Title": "Your Title 10",
        "Rights": "Your Copyright Notice 11",
        "Credit": "Your Credit Line 12",
        "State": "Your Province or State 13",
        "CaptionWriter": "Your Caption Writer 14",
    }
    assert write_metadata(video_binary, updates) == video_updated_binary


def test_get_video_from_photo_binary(image_binary) -> None:
    from superdesk.media.image import read_metadata
    from superdesk.media.video import get_video_from_photo

    video = {
        "Description": (
            "The Montreal Police logo is seen on "
            "a police car in Montreal on Wednesday, July 8, 2020. "
            "THE CANADIAN PRESS/Paul Chiasson"
        ),
        "CaptionWriter": "pch",
        "City": "Montreal",
        "Country": "Canada",
        "CountryCode": "CAN",
        "Creator": ["Paul Chiasson"],
        "AuthorsPosition": "stf",
        "TransmissionReference": "DPI755",
        "Instructions": "EDS NOTE:A FILE PHOTO",
        "Title": "MORT PIÉTONNE MONTRÉAL 20201014",
        "Credit": "The Canadian Press",
        "State": "PQ",
    }
    assert get_video_from_photo(read_metadata(image_binary)) == video
