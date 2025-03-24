from superdesk.core.module import Module
from .service import ArchiveService
from .module import archive_resource_config

__all__ = ["ArchiveService"]

module = Module(name="superdesk.archive_async", resources=[archive_resource_config])
