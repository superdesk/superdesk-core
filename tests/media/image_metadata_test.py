from pytest import fixture
from superdesk.media.image import (
    PhotoMetadata,
    PhotoMetadataMapping,
    get_metadata_from_item,
    read_metadata,
    write_metadata,
)
from superdesk.types import Item

from .. import fixture_path


@fixture
def image_binary() -> bytes:
    image_path = fixture_path("cp.jpg", "media")
    with open(image_path, mode="rb") as f:
        return f.read()


def test_photo_metadata_read_write(image_binary) -> None:
    metadata = read_metadata(image_binary)
    assert metadata == PhotoMetadata(
        Description="The Montreal Police logo is seen on a police car in Montreal on Wednesday, July 8, 2020. THE CANADIAN PRESS/Paul Chiasson",
        DescriptionWriter="pch",
        Headline="",
        City="Montreal",
        Country="Canada",
        CountryCode="CAN",
        Creator=["Paul Chiasson"],
        CreatorsJobtitle="stf",
        JobId="DPI755",
        Instructions="EDS NOTE:A FILE PHOTO",
        Title="MORT PIÉTONNE MONTRÉAL 20201014",
        CopyrightNotice="",
        CreditLine="The Canadian Press",
        ProvinceState="PQ",
    )

    updated = PhotoMetadata(
        Description="description",
        DescriptionWriter="description writer",
        Headline="headline",
        City="city",
        Country="country",
        CountryCode="FOO",
        Creator=["creator"],
        CreatorsJobtitle="creators jobtitle",
        JobId="jobid",
        Instructions="instructions",
        Title="title",
        CopyrightNotice="notice",
        CreditLine="credit",
        ProvinceState="state",
    )

    next_image = write_metadata(image_binary, updated)

    metadata = read_metadata(next_image)
    assert metadata == updated


def test_get_metadata_from_item() -> None:
    item = Item(
        headline="foo",
        slugline="bar",
        extra={
            "filename": "baz",
        },
    )
    mapping: PhotoMetadataMapping = dict(
        headline="Headline",
        slugline="Title",
    )
    mapping["extra.filename"] = "JobId"
    metadata = get_metadata_from_item(item, mapping)
    assert metadata == PhotoMetadata(
        Headline="foo",
        Title="bar",
        JobId="baz",
    )
