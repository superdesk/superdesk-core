from typing import Annotated
from superdesk.core.module import Module
from superdesk.core.resources import ResourceConfig, ResourceModel, RestEndpointConfig
from superdesk.core.resources.service import AsyncResourceService
from superdesk.core.resources.validators import validate_data_relation_async


class RingBearer(ResourceModel):
    name: str


class RingBearerService(AsyncResourceService[RingBearer]):
    resource_name = "ring_bearer"


class RingPower(ResourceModel):
    name: str


class RingPowerService(AsyncResourceService[RingPower]):
    resource_name = "ring_power"


class BaseRing(ResourceModel):
    name: str
    bearer: Annotated[str, validate_data_relation_async("ring_bearer")]


class RingOfPower(BaseRing):
    """Inherits from base rings and adds an extra relation"""

    power: Annotated[str, validate_data_relation_async("ring_power")]


class RingOfPowerService(AsyncResourceService[RingOfPower]):
    resource_name = "ring_of_power"


resource_config_bearer = ResourceConfig(
    name="ring_bearer",
    data_class=RingBearer,
    service=RingBearerService,
    rest_endpoints=RestEndpointConfig(auth=False),
)

resource_config_power = ResourceConfig(
    name="ring_power",
    data_class=RingPower,
    service=RingPowerService,
    rest_endpoints=RestEndpointConfig(auth=False),
)

resource_config_ring_of_power = ResourceConfig(
    name="ring_of_power",
    data_class=RingOfPower,
    service=RingOfPowerService,
    rest_endpoints=RestEndpointConfig(
        auth=False,
        populate_item_hateoas=True,
    ),
)

resource_config_ring_of_power_no_hateoas = ResourceConfig(
    name="ring_of_power_no_hateoas",
    data_class=RingOfPower,
    service=RingOfPowerService,
    rest_endpoints=RestEndpointConfig(
        auth=False,
        populate_item_hateoas=False,
    ),
)


module = Module(
    name="tests.module_related_resources",
    resources=[
        resource_config_bearer,
        resource_config_power,
        resource_config_ring_of_power,
        resource_config_ring_of_power_no_hateoas,
    ],
)
