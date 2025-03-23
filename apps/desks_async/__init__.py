from superdesk.core.module import Module
from .desks_async_service import DesksAsyncService
from .module import desks_resource_config
from .utils import get_desk_name_by_id, add_member_to_desk

__all__ = ["DesksAsyncService", "get_desk_name_by_id", "add_member_to_desk"]

module = Module(name="apps.desks_async", resources=[desks_resource_config])
