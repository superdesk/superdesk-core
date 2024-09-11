from superdesk.core.module import Module
from superdesk.core.resources import ResourceConfig, ResourceModel, AsyncResourceService, RestEndpointConfig


class CompanyResource(ResourceModel):
    name: str


class CompanyService(AsyncResourceService[CompanyResource]):
    resource_name = "companies"


companies_resource_config = ResourceConfig(
    name="companies",
    data_class=CompanyResource,
    service=CompanyService,
    rest_endpoints=RestEndpointConfig(),
)

module = Module(name="tests.company", resources=[companies_resource_config])
