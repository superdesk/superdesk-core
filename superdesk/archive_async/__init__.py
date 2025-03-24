from superdesk.core.module import Module
from .service import AsyncArchiveService
from .module import archive_resource_config

__all__ = ["AsyncArchiveService"]

module = Module(name="superdesk.archive_async", resources=[archive_resource_config])
