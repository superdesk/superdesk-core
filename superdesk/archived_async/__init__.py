from superdesk.core.module import Module
from .service import ArchivedService
from .module import archived_resource_config

__all__ = ["ArchivedService"]

module = Module(name="superdesk.archived_async", resources=[archived_resource_config])
