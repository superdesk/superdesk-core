from typing import Dict, List
from superdesk.publish import SUBSCRIBER_TYPES


def is_digital(subscriber: Dict) -> bool:
    return subscriber.get("subscriber_type", "") in {SUBSCRIBER_TYPES.DIGITAL, SUBSCRIBER_TYPES.ALL}


def filter_digital(subscribers: List[Dict]) -> List[Dict]:
    return [s for s in subscribers if is_digital(s)]


def filter_non_digital(subscribers: List[Dict]) -> List[Dict]:
    return [s for s in subscribers if not is_digital(s)]
