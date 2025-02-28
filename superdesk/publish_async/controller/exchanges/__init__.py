from superdesk.core.utils import load_class_from_config
from .exchange_factory import ExchangeFactory


__all__ = ["ExchangeFactory", "get_exchange_factory"]


def get_exchange_factory() -> ExchangeFactory:
    factory_class = load_class_from_config(ExchangeFactory, "PUBLISH_EXCHANGE_FACTORY")
    return factory_class()
