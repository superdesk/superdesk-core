from superdesk.core.elastic.common import ElasticResourceConfig
from superdesk.core.module import Module
from superdesk.core.resources import ResourceModel, ResourceConfig


class Upload(ResourceModel):
    pass


upload_model_config = ResourceConfig(name="upload", data_class=Upload, elastic=ElasticResourceConfig())
