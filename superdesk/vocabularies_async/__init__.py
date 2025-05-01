from superdesk.core.module import Module
from .service import VocabulariesService
from .module import vocabularies_resource_config
from .utils import get_cv_items, get_languages

__all__ = ["VocabulariesService", "get_cv_items", "get_languages"]

module = Module(name="superdesk.vocabularies_async", resources=[vocabularies_resource_config])
