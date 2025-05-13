from bson import ObjectId
from superdesk.types import SubscribersResource, SubscriberType, SubscriberSequenceSettings, SubscriberDestination

from .products import TEXT_PRODUCT_ID, NSW_PRODUCT_ID, ABCDEF_PRODUCT_ID

SUB1_ID = ObjectId()
SUB2_ID = ObjectId()
SUB3_ID = ObjectId()
SUB4_ID = ObjectId()
SUB5_ID = ObjectId()

TEXT_SUBSCRIBER_ID = ObjectId()


def text_subscriber() -> SubscribersResource:
    return SubscribersResource(
        id=TEXT_SUBSCRIBER_ID,
        name="text",
        email="text@subscriber.com",
        is_active=True,
        subscriber_type=SubscriberType.ALL,
        sequence_num_settings=SubscriberSequenceSettings(min=1, max=100),
        products=[TEXT_PRODUCT_ID],
        destinations=[
            SubscriberDestination(
                name="dest1",
                format="nitf",
                delivery_type="File",
                config={"file_path": "/tmp/"},
            ),
        ],
    )


def sub1_subscriber() -> SubscribersResource:
    return SubscribersResource(
        id=SUB1_ID,
        name="sub1",
        email="test@test.com",
        is_active=True,
        subscriber_type=SubscriberType.WIRE,
        media_type="media",
        sequence_num_settings=SubscriberSequenceSettings(min=1, max=10),
        products=[NSW_PRODUCT_ID],
        destinations=[
            SubscriberDestination(
                name="dest1",
                format="nitf",
                delivery_type="ftp",
                config={"address": "127.0.0.1", "username": "test"},
            ),
        ],
    )


def sub2_subscriber() -> SubscribersResource:
    return SubscribersResource(
        id=SUB2_ID,
        name="sub2",
        email="test@test.com",
        is_active=True,
        subscriber_type=SubscriberType.WIRE,
        media_type="media",
        sequence_num_settings=SubscriberSequenceSettings(min=1, max=10),
        products=[NSW_PRODUCT_ID],
        destinations=[
            SubscriberDestination(
                name="dest2",
                format="nitf",
                delivery_type="filecopy",
                config={"address": "/share/copy"},
            ),
            SubscriberDestination(
                name="dest3",
                format="nitf",
                delivery_type="email",
                config={"recipients": "test@sourcefabric.org"},
            ),
        ],
    )


def sub3_subscriber() -> SubscribersResource:
    return SubscribersResource(
        id=SUB3_ID,
        name="sub3",
        email="test@test.com",
        is_active=True,
        subscriber_type=SubscriberType.DIGITAL,
        media_type="media",
        sequence_num_settings=SubscriberSequenceSettings(min=1, max=10),
        products=[NSW_PRODUCT_ID],
        destinations=[
            SubscriberDestination(
                name="dest1",
                format="nitf",
                delivery_type="ftp",
                config={"address": "127.0.0.1", "username": "test"},
            ),
        ],
    )


def sub4_subscriber() -> SubscribersResource:
    return SubscribersResource(
        id=SUB4_ID,
        name="sub4",
        email="test@test.com",
        is_active=True,
        subscriber_type=SubscriberType.WIRE,
        media_type="media",
        sequence_num_settings=SubscriberSequenceSettings(min=1, max=10),
        products=[NSW_PRODUCT_ID],
        destinations=[
            SubscriberDestination(
                name="dest1",
                format="nitf",
                delivery_type="ftp",
                config={"address": "127.0.0.1", "username": "test"},
            ),
        ],
    )


def sub5_subscriber() -> SubscribersResource:
    return SubscribersResource(
        id=SUB5_ID,
        name="sub5",
        email="test@test.com",
        is_active=True,
        subscriber_type=SubscriberType.ALL,
        media_type="media",
        sequence_num_settings=SubscriberSequenceSettings(min=1, max=10),
        products=[NSW_PRODUCT_ID, ABCDEF_PRODUCT_ID],
        codes="xyz,klm",
        destinations=[
            SubscriberDestination(
                name="dest1",
                format="nitf",
                delivery_type="ftp",
                config={"address": "127.0.0.1", "username": "test"},
            ),
        ],
    )


def all_subscribers() -> list[SubscribersResource]:
    return [
        sub1_subscriber(),
        sub2_subscriber(),
        sub3_subscriber(),
        sub4_subscriber(),
        sub5_subscriber(),
    ]
