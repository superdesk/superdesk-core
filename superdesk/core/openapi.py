from typing import cast
from importlib import import_module
from inspect import signature
from enum import Enum
from copy import deepcopy

from yaml import dump
from pydantic.json_schema import GenerateJsonSchema

from superdesk import __version__
from superdesk.core import json
from superdesk.core.resources import BaseModel
from superdesk.core.module import Module
from superdesk.core.types import Endpoint, EndpointGroup


class OpenApiSchemaGenerator(GenerateJsonSchema):
    @classmethod
    def get_model_schema(cls, model: type[BaseModel]) -> dict:
        return model.model_json_schema(schema_generator=cls, ref_template="#/components/schemas/{model}")

    def generate(self, schema, mode="serialization"):
        json_schema = super().generate(schema, mode=mode)
        self._remove_excluded_fields_for_docs(json_schema)

        def _process_node(node: dict) -> None:
            self._remove_none_from_optional_fields(node)
            for field in ("elastic_mapping", "include_in_parent", "nested"):
                value = node.pop(field, None)
                if value:
                    node[f"x-{field}"] = value

            if node.get("items"):
                _process_node(node["items"])

        for field_config in json_schema.get("properties", {}).values():
            _process_node(field_config)

        for field_config in json_schema.get("components", {}).get("parameters", {}).values():
            _process_node(field_config)

        for resource_config in json_schema.get("$defs", {}).values():
            for field_config in resource_config.get("properties", {}).values():
                _process_node(field_config)
            _process_node(resource_config)

        return json_schema

    def _remove_excluded_fields_for_docs(self, json_schema: dict) -> None:
        """Remove all properties from the supplied schema that have the ``exclude_from_docs`` attribute set to True.

        Will also remove the field from ``required`` if present.
        """

        for field in list(json_schema.get("properties", {}).keys()):
            if json_schema["properties"][field].get("exclude_from_docs"):
                json_schema["properties"].pop(field)
                if field in json_schema.get("required", []):
                    json_schema["required"].remove(field)

    def _remove_none_from_optional_fields(self, node: dict) -> None:
        """Remove the ``None`` choice for an optional field

        Since Pydantic doesn't support the concept of a non-nullable optional field,
        we must remove this option ourselves here.
        """

        if node.get("default", None) is not None or node.get("type") or not node.get("anyOf"):
            # Either type is already defined or this field has a non-none default value
            return

        choices = [choice for choice in node["anyOf"] if "type" not in choice or choice["type"] not in [None, "null"]]
        if len(choices) == 1:
            # Since there is 1 left after removing the ``None`` choice, this must be the type
            choice = choices[0]
            node.pop("anyOf", None)
            node.update(choice)
            node.pop("default", None)


class OpenAPISpec:
    """
    Represents an OpenAPI Specification builder.

    This class provides methods to construct and manage an OpenAPI Specification
    as a dictionary. It includes support for adding OpenAPI components such as
    tags, servers, parameters, responses, schemas, paths, and modules.

    The primary goal of this class is to facilitate the auto-generation of an OpenAPI spec for an API
    that uses the new Pydantic-based type system.
    """

    #: The dictionary used to store the OpenAPI sepcification as it's being built
    spec: dict

    def __init__(
        self,
        title: str = "Insert title here",
        description: str = "Insert description here",
        schema_version: str = "3.1.1",
        api_version: str = __version__,
    ):
        self.spec = {
            "openapi": schema_version,
            "info": {
                "title": title,
                "description": description,
                "version": api_version,
            },
            "servers": [],
            "tags": [],
            "paths": {},
            "components": {
                "parameters": {},
                "responses": {},
                "schemas": {},
            },
        }

    def add_tag(self, name: str, description: str) -> "OpenAPISpec":
        """
        Adds a new tag to the OpenAPI specification.

        This method allows the user to add a tag with a specific name and description
        to the OpenAPI spec. Tags are used in OpenAPI documents to group endpoints
        together and provide additional context about the API.

        :param name: The name of the tag to add.
        :param description: A brief description of the tag.
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        self.spec["tags"].append({"name": name, "description": description})
        return self

    def add_server(self, url: str, description: str) -> "OpenAPISpec":
        """
        Adds a server to the OpenAPI specification.

        This method appends a new server object to the "servers" list in the OpenAPI specification.
        The server object includes a URL and an optional description of the server's functionality.

        :param url: The URL of the server to be added.
        :param description: A description of the server's purpose.
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        self.spec["servers"].append({"url": url, "description": description})
        return self

    def add_param(self, name: str, spec: dict) -> "OpenAPISpec":
        """
        Adds a parameter definition to the OpenAPI specification.

        This method allows adding a new parameter to the "components.parameters" section
        of the OpenAPI specification. The provided parameter metadata is stored under the
        specified name.

        :param name: The name of the parameter to be added.
        :param spec: A dictionary containing the specification details of the parameter.
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        self.spec["components"]["parameters"][name] = spec
        return self

    def add_response(self, name: str, spec: dict) -> "OpenAPISpec":
        """
        Adds a response specification to the OpenAPI specification.

        This method allows adding a named response specification to the OpenAPI
        components under 'responses'. The response specification is defined as
        a dictionary containing details about the response.

        :param name: The name of the response to be added.
        :param spec: A dictionary containing the specification details of the response.
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        self.spec["components"]["responses"][name] = spec
        return self

    def add_schema(self, name: str, spec: dict) -> "OpenAPISpec":
        """
        Adds a new schema to the OpenAPI specification.

        This method allows adding a schema to the 'schemas' section of the OpenAPI
        specification, which is located under the 'components' section. The added
        schema is referenced by the given name and must be provided as a dictionary.

        :param name: The name of the schema to be added.
        :param spec: A dictionary containing the schema details.
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        self.spec["components"]["schemas"][name] = spec
        return self

    def add_schemas(self, specs: dict) -> "OpenAPISpec":
        """
        Updates the OpenAPI specification with additional schemas.

        Updates the 'schemas' section of the OpenAPI specification under
        'components' with the given dictionary of schema definitions.

        :param specs: A dictionary containing schema definitions to be added
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        self.spec["components"]["schemas"].update(specs)
        return self

    def add_path(self, url: str, spec: dict) -> "OpenAPISpec":
        """
        Adds a new path and its specification to the OpenAPI specification.

        This method updates the paths section of the OpenAPI specification by adding
        a new path and its corresponding specification. It ensures the OpenAPI
        specification object remains updated with the provided path information.

        :param url: The URL path to be added as a string.
        :param spec: A dictionary containing the specification for the given path.
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        self.spec["paths"][url] = spec
        return self

    def add_module_from_path(self, module_path: str) -> "OpenAPISpec":
        """
        Adds a Superdesk module to the specification from the given module path.

        This method attempts to dynamically import a Python module using the provided
        module path. If the module is successfully imported and contains a valid
        resource (attribute named 'module') of type Module, it adds it to the current
        specification. Errors in importing or accessing the module result in the method
        returning the current instance without adding the module.

        :param module_path: The dot notation path of the Python module to import.
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        imported_module = import_module(module_path)
        if not imported_module:
            print("Failed to import the module")
            return self

        module_value: Module | None = getattr(imported_module, "module", None)
        if not module_value:
            print("Failed to get resource from module")
            return self
        elif not isinstance(module_value, Module):
            print("Invalid attribute on module")
            return self

        self.add_module(module_value)
        return self

    def add_module_attribute_from_path(self, module_path: str) -> "OpenAPISpec":
        """
        Adds a module attribute to the OpenAPISpec instance using the given module path.

        This method attempts to resolve the module and its attributes from the given
        path and subsequently adds the resolved object, if valid, to the
        OpenAPISpec instance. Supported objects include `Endpoint` instances and
        subclasses of `BaseModel`. If the object is invalid or the module cannot
        be imported, the method returns without making any modifications.

        :param module_path: The path of the module and its attribute in the format
            "module_name:attribute_path". If the attribute path is empty, the
            entire module is added.
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        if ":" not in module_path:
            return self.add_module_from_path(module_path)

        mod_name, has_attrs, attrs = module_path.partition(":")

        imported_module = cast(type[BaseModel] | Endpoint | None, import_module(mod_name))
        if not imported_module:
            print("Failed to import the module")
            return self

        obj: type[BaseModel] | Endpoint = imported_module
        if has_attrs:
            parts = attrs.split(".")
            obj = imported_module
            for part in parts:
                obj = getattr(obj, part)

        if isinstance(obj, Endpoint):
            self.add_endpoint(obj)
        elif issubclass(obj, BaseModel):
            self.add_model(obj)

        return self

    def add_module(self, module: Module) -> "OpenAPISpec":
        """
        Adds all resources and endpoints from a given Superdesk module to the current spec.

        :param module: The module containing resources and endpoints to be added.
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        for resource in module.resources or []:
            self.add_model(resource.data_class)

        for endpoint in module.endpoints or []:
            self.add_endpoint(endpoint)

        return self

    def add_endpoint(self, endpoint: Endpoint | EndpointGroup) -> "OpenAPISpec":
        """
        Adds an API endpoint or a group of endpoints to the OpenAPI specification.

        This method handles the inclusion of a single endpoint or iterates over a
        group of endpoints (`EndpointGroup`). It builds and populates the OpenAPI
        specification fields, including the parameters and schema information
        for query and path arguments, HTTP methods, responses, tags, and more,
        from the provided `Endpoint` or `EndpointGroup` object. The functionality
        includes generating model schemas for function parameters based on
        `Pydantic` models (`BaseModel`).

        :param endpoint: An instance of either `Endpoint` or `EndpointGroup` to be added to the OpenAPI specification.
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        if isinstance(endpoint, EndpointGroup):
            for sub_endpoint in endpoint.endpoints:
                self.add_endpoint(sub_endpoint)
            return self

        endpoint_spec: dict = {}
        func_params = signature(endpoint.func).parameters
        param_spec: list[dict] = []

        def _add_func_arg(arg_name: str, request_location: str) -> None:
            if not func_params.get(arg_name) or func_params[arg_name].annotation is None:
                # Function argument does not exist, no need to add to the schema
                return
            elif not issubclass(func_params[arg_name].annotation, BaseModel):
                # Function argument is not a BaseModel, unable to add to the schema
                return

            model: type[BaseModel] = func_params[arg_name].annotation
            param_schema = OpenApiSchemaGenerator.get_model_schema(model)

            if request_location == "path":
                endpoint_spec["parameters"] = []

            for field, info in model.model_fields.items():
                if request_location == "path":
                    endpoint_spec["parameters"].append({"$ref": f"#/components/parameters/{field}"})
                else:
                    param_spec.append({"$ref": f"#/components/parameters/{field}"})

                spec = {
                    "name": field,
                    "in": request_location,
                    "description": param_schema["properties"][field].pop("description", ""),
                    "schema": param_schema["properties"][field],
                }
                if info.is_required():
                    spec["required"] = True

                self.add_param(field, spec)

        _add_func_arg("params", "query")
        _add_func_arg("args", "path")

        for http_method in endpoint.methods:
            if http_method.lower() == "options":
                continue

            endpoint_spec[http_method.lower()] = dict(
                tags=endpoint.tags,
                summary=endpoint.summary,
                description=endpoint.description,
            )
            if param_spec:
                endpoint_spec[http_method.lower()]["parameters"] = param_spec
            if endpoint.responses:
                endpoint_spec[http_method.lower()]["responses"] = endpoint.responses

        self.add_path("/" + endpoint.url, endpoint_spec)
        return self

    def add_model(self, model: type[BaseModel], tags: list[str] | None = None) -> "OpenAPISpec":
        """
        Adds a given Pydantic based model to the OpenAPI specification and generates its schema.

        This function processes the provided model by generating its schema using
        the OpenApiSchemaGenerator. It then adds any sub-schemas under the
        "$defs" key to the main OpenAPI specification schemas. Finally, it adds
        the primary schema of the model to the OpenAPI specification.

        :param model: The model class to generate and add the schema for.
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        schema = OpenApiSchemaGenerator.get_model_schema(model)
        self.add_schemas(schema.pop("$defs", {}))
        if tags:
            schema["x-tags"] = tags
        self.add_schema(model.__name__, schema)
        return self

    def add_enum(self, enum_type: type[Enum]) -> "OpenAPISpec":
        """
        Adds the given enumeration type to the OpenAPI specification.

        :param enum_type: The enumeration type to add, whose values will be included in the schema.
        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        self.add_schema(
            enum_type.__name__,
            {
                "type": "string",  # TODO: Support other enum value types
                "enum": [member.value for member in enum_type],
            },
        )
        return self

    def remove_additional_properties_from_top_level(self) -> "OpenAPISpec":
        """
        Removes 'additionalProperties' from all top-level schemas in the OpenAPI specification.

        Iterates through the schemas defined under the 'components' section of the OpenAPI specification
        and removes the 'additionalProperties' field if it exists. This operation is performed directly
        on the specification's schema objects.

        :return OpenAPISpec: Returns the current instance of OpenAPISpec to allow method chaining.
        """

        for key, schema in self.spec["components"]["schemas"].items():
            schema.pop("additionalProperties", None)
        return self

    def to_dict(self) -> dict:
        """Converts the specification to a dictionary, ready to turn into JSON or YAML."""

        spec = deepcopy(self.spec)
        for attribute in {"servers", "tags", "paths"}:
            if not spec.get(attribute):
                spec.pop(attribute, None)

        for attribute in {"parameters", "responses", "schemas"}:
            if not spec["components"].get(attribute):
                spec["components"].pop(attribute, None)

        if not spec["components"]:
            spec.pop("components", None)

        return spec

    def to_string(self, output_format: str, pretty_print: bool = True) -> str:
        """
        Converts the specification to either JSON or YAML string format based on the provided
        output format. Optionally, the output can be pretty-printed with indentation.

        :param output_format: The desired output format for the specification. It must be either "json" or "yaml".
        :param pretty_print: If True, the output will be formatted with indentation for better readability. Defaults to True.
        :return str: The formatted specification as a string.
        :raises ValueError: If the provided output format is neither "json" nor "yaml".
        """

        spec = self.to_dict()
        kwargs: dict = {} if not pretty_print else {"indent": 4}
        if output_format == "json":
            return json.dumps(spec, **kwargs)
        elif output_format == "yaml":
            kwargs["sort_keys"] = True
            return dump(spec, sort_keys=False)

        raise ValueError(f"Unknown output format: {output_format}")
