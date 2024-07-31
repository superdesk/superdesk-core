from superdesk.core.module import Module
from .resources import upload_model_config

module = Module(name="tests.assets", resources=[upload_model_config])
