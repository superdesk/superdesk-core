from superdesk.core.module import Module
from .desks_async_service import DesksAsyncService
from .module import desks_resource_config

__all__ = ["DesksAsyncService"]

module = Module(name="apps.desks", resources=[desks_resource_config])
