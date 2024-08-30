from superdesk.core.module import Module

from .model import Content
from .resources import ContentResourceService, content_model_config

__all__ = [
    "Content",
    "ContentResourceService",
    "content_model_config",
]

module = Module(
    name="tests.content",
    resources=[content_model_config],
)
