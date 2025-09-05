from quart import Response
from quart.testing import QuartClient


from superdesk.core.resources import ResourceModel


class TestClient(QuartClient):
    async def open(self, *args, **kwargs) -> Response:
        """
        Appends the request path to the response object for later debugging
        """

        response = await super().open(*args, **kwargs)
        response.request_path = kwargs.get("path", args[0] if args else "/")  # type: ignore[attr-defined]
        return response

    def model_instance_to_json(self, model_instance: ResourceModel):
        return model_instance.to_dict(mode="json")

    async def post(self, *args, **kwargs) -> Response:
        if "json" in kwargs:
            if isinstance(kwargs["json"], ResourceModel):
                kwargs["json"] = self.model_instance_to_json(kwargs["json"])
            elif isinstance(kwargs["json"], list):
                kwargs["json"] = [
                    self.model_instance_to_json(item) if isinstance(item, ResourceModel) else item
                    for item in kwargs["json"]
                ]
            elif isinstance(kwargs["json"], dict):
                kwargs["json"] = {
                    key: self.model_instance_to_json(value) if isinstance(value, ResourceModel) else value
                    for key, value in kwargs["json"].items()
                }

        return await super().post(*args, **kwargs)
