from typing import Any
from typing_extensions import Self, override

from pydantic import BaseModel as PydanticModel, AliasChoices

from .web import Request


class BaseModel(PydanticModel):
    @classmethod
    def get_field_names(cls) -> list[str]:
        names: list[str] = []
        for field, info in cls.model_fields.items():
            if isinstance(info.validation_alias, AliasChoices):
                # Exclude `AliasPath` instances from choices, as we won't be able to
                # translate that into a field name
                names.extend([choice for choice in info.validation_alias.choices if isinstance(choice, str)])
            else:
                names.append(info.alias or field)
        return names

    @classmethod
    def from_url_args(cls, request: "Request", default_values: dict[str, Any] | None = None):
        if default_values is None:
            default_values = {}

        value_dict: dict[str, Any] = {}
        for field in cls.get_field_names():
            value = request.get_url_arg(field) or default_values.get(field)
            if value:
                value_dict[field] = value
        return cls.from_dict(value_dict)

    @override
    @classmethod
    def model_validate(
        cls,
        obj: dict[str, Any],
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, Any] | None = None,
        include_unknown: bool = False,
    ) -> Self:
        """Construct a model instance from the provided dictionary, and validate its values

        :param obj: Dictionary of values used to construct the model instance
        :param strict: Whether to enforce types strictly
        :param from_attributes: Whether to extract data from object attributes
        :param context: Additional context to pass to the validator
        :param include_unknown: Whether to include fields not defined in the ResourceModel
        :raises Pydantic.ValidationError: If validation fails
        :rtype: ResourceModel
        :returns: The validated model instance
        """

        if not include_unknown:
            data = {field: value for field, value in obj.items() if field in cls.get_field_names()}
        else:
            data = obj.copy()
            data.pop("_type", None)

        instance = super().model_validate(
            data,
            strict=strict,
            from_attributes=from_attributes,
            context=context,
        )

        return instance

    @classmethod
    def from_dict(
        cls,
        values: dict[str, Any],
        context: dict[str, Any] | None = None,
        include_unknown: bool = False,
    ) -> Self:
        """Construct a model instance from the provided dictionary, and validate its values

        :param values: Dictionary of values used to construct the model instance
        :param context: Additional context to pass to the validator
        :param include_unknown: Whether to include fields not defined in the ResourceModel
        :raises Pydantic.ValidationError: If validation fails
        :rtype: ResourceModel
        :returns: The validated model instance
        """

        return cls.model_validate(values, context=context, include_unknown=include_unknown)

    @classmethod
    def from_json(cls, data: str | bytes | bytearray, **kwargs):
        return cls.model_validate_json(data, **kwargs)

    def to_dict(self, **kwargs) -> dict[str, Any]:
        """
        Convert the model instance to a dictionary representation with non-JSON-serializable Python objects.

        :param kwargs: Optional keyword arguments to override the default parameters of model_dump.
        :rtype: dict[str, Any]
        :returns: A dictionary representation of the model instance with field aliases.
                Only fields that are set (non-default) will be included.
        """
        default_params: dict[str, Any] = {"by_alias": True, "exclude_unset": True}
        default_params.update(kwargs)
        model_dict = self.model_dump(**default_params)
        return model_dict

    def to_json(self, **kwargs) -> str:
        """
        Convert the model instance to a JSON serializable dictionary.

        :param kwargs: Optional keyword arguments to override the default parameters of model_dump_json.
        :rtype: str
        :return: A JSON-compatible dictionary representation of the model instance with field aliases.
                Only fields that are set (non-default) will be included.
        """
        default_params: dict[str, Any] = {"by_alias": True, "exclude_unset": True}
        default_params.update(kwargs)
        return self.model_dump_json(**default_params)
