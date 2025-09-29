from typing import Dict, List, Literal, TypedDict


class MediaMetadata(TypedDict, total=False):
    Description: str | None
    CaptionWriter: str | None
    Headline: str | None
    Instructions: str | None
    TransmissionReference: str | None
    Title: str | None
    Creator: List[str] | str | None
    AuthorsPosition: str | None
    Rights: str | None
    City: str | None
    Country: str | None
    CountryCode: str | None
    Credit: str | None
    State: str | None
    Location: str | None
    CreatorContactInfo: str | None
    Language: str | None
    Destination: str | None
    ServiceIdentifier: str | None
    ProductID: str | None
    DateSent: str | None
    TimeSent: str | None
    EditStatus: str | None
    Urgency: str | None
    SubjectCode: str | None
    Category: str | None
    SupplementalCategories: str | None
    Subject: str | None
    LocationCode: str | None
    LocationName: str | None
    ReleaseDate: str | None
    ReleaseTime: str | None
    ExpirationDate: str | None
    ExpirationTime: str | None
    TimeCreated: str | None
    Source: str | None
    DateCreated: str | None
    DescriptionWriter: str
    JobId: str
    CreatorsJobtitle: str
    ProvinceState: str
    CopyrightNotice: str
    CreditLine: str


MediaMetadataKeys = set(MediaMetadata.__annotations__.keys())

MediaMetadataMappingKeys = Literal[
    "Description",
    "DescriptionWriter",
    "Headline",
    "Instructions",
    "JobId",
    "Title",
    "Creator",
    "CreatorsJobtitle",
    "City",
    "ProvinceState",
    "Country",
    "CountryCode",
    "CopyrightNotice",
    "CreditLine",
]

MediaMetadataMapping = Dict[str, MediaMetadataMappingKeys]
