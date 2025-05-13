from dataclasses import asdict
from superdesk.core.web import EndpointGroup
from superdesk.core.types import Request, Response
from superdesk.publish_async.utils.filter_conditions import get_available_filter_params

filter_conditions_parameters_endpoint: EndpointGroup = EndpointGroup("filter_conditions_parameters", __name__)


@filter_conditions_parameters_endpoint.endpoint(
    "filter_conditions/parameters",
    methods=["GET"],
)
async def filter_conditions_parameters(args: None, params: None, request: Request) -> Response:
    filter_params = await get_available_filter_params()
    filter_params_as_dict = [asdict(filter_param) for filter_param in filter_params]
    return Response({"_items": filter_params_as_dict})
