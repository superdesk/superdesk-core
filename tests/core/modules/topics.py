from typing import Annotated
from superdesk.core.module import Module
from superdesk.core.resources import (
    ResourceConfig,
    ResourceModel,
    AsyncResourceService,
    RestEndpointConfig,
    RestParentLink,
)
from superdesk.core.resources.validators import validate_data_relation_async

from .users import user_model_config
from .company import companies_resource_config


class TopicFolder(ResourceModel):
    name: str
    section: str


class UserFolder(TopicFolder):
    user: Annotated[str, validate_data_relation_async(user_model_config.name)]


class UserFolderService(AsyncResourceService[UserFolder]):
    resource_name = "user_topic_folders"


user_folder_config = ResourceConfig(
    name="user_topic_folders",
    datasource_name="topic_folders",
    data_class=UserFolder,
    service=UserFolderService,
    rest_endpoints=RestEndpointConfig(
        parent_links=[
            RestParentLink(
                resource_name=user_model_config.name,
                model_id_field="user",
            )
        ],
        url="topic_folders",
    ),
)


class CompanyFolder(TopicFolder):
    company: str


class CompanyFolderService(AsyncResourceService[CompanyFolder]):
    resource_name = "company_topic_folders"


company_folder_config = ResourceConfig(
    name="company_topic_folders",
    datasource_name="topic_folders",
    data_class=CompanyFolder,
    service=CompanyFolderService,
    rest_endpoints=RestEndpointConfig(
        parent_links=[
            RestParentLink(
                resource_name=companies_resource_config.name,
                model_id_field="company",
            )
        ],
        url="topic_folders",
    ),
)


module = Module(
    name="tests.multi_sources",
    resources=[user_folder_config, company_folder_config],
)
