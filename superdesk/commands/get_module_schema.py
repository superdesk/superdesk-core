import click

from superdesk.core.openapi import OpenAPISpec

from .async_cli import cli


@cli.command("module:get_module_schema")
@click.option("-m", "--modules", required=True)
@click.option("-t", "--type", "output_type", required=False, default="yaml")
@click.option("-p", "--pretty-print", is_flag=True, default=False)
def get_module_schema(modules: str, output_type: str, pretty_print: bool) -> None:
    """
    Generate a JSON Schema for an async module

    Example:
    ::

        $ python manage.py module:get_schema -m planning.content_api
        $ python manage.py module:get_schema -pt yaml -m planning.content_api
        $ python manage.py module:get_schema -pt json -m planning.content_api
    """

    spec = OpenAPISpec()

    for module_path in modules.split(","):
        spec.add_module_from_path(module_path)

    spec.remove_additional_properties_from_top_level()

    print(spec.to_string("yaml" if output_type == "yaml" else "json", pretty_print=pretty_print))


@cli.command("module:get_schema")
@click.option("-m", "--module", required=True)
@click.option("-t", "--type", "output_type", required=False, default="yaml")
@click.option("-p", "--pretty-print", is_flag=True, default=False)
def get_schema(module: str, output_type: str, pretty_print: bool) -> None:
    """
    Generate a JSON Schema for an async module attribute

    Example:
    ::

        $ python manage.py module:get_schema -m planning.content_api
        $ python manage.py module:get_schema -pt yaml -m planning.content_api
        $ python manage.py module:get_schema -pt json -m planning.content_api
    """

    spec = OpenAPISpec()
    spec.add_module_attribute_from_path(module)
    spec.remove_additional_properties_from_top_level()

    print(spec.to_string("yaml" if output_type == "yaml" else "json", pretty_print=pretty_print))
