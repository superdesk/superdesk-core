from superdesk.core.module import Module
from superdesk.core.resources import ResourceModel, ResourceConfig, ElasticResourceConfig


class Upload(ResourceModel):
    pass


upload_model_config = ResourceConfig(name="upload", data_class=Upload, elastic=ElasticResourceConfig())
