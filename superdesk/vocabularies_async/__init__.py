from superdesk.core.module import Module
from .service import VocabulariesService
from .module import vocabularies_resource_config

__all__ = ["VocabulariesService"]

module = Module(name="superdesk.vocabularies_async", resources=[vocabularies_resource_config])
