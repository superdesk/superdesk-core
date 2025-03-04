from superdesk.core.resources import ResourceConfig, MongoResourceConfig, MongoIndexOptions
from superdesk.types import SequencesResource


sequences_resource_config = ResourceConfig(
    name="sequences",
    data_class=SequencesResource,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(
                name="key_1",
                keys=[("key", 1)],
                unique=True,
            )
        ]
    ),
    etag_ignore_fields=["sequence_number", "name"],
)
