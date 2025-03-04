from superdesk.core import AsyncSignal
from superdesk.types import FilterConditionFieldParam


on_get_available_filter_params = AsyncSignal[list[FilterConditionFieldParam]]("on_get_available_filter_params")
