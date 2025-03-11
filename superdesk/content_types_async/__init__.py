from superdesk.core.module import Module
from .service import ContentTypesService
from .module import content_types_resource_config

__all__ = ["ContentTypesService"]

module = Module(name="superdesk.content_types_async", resources=[content_types_resource_config])
