from abc import abstractmethod, ABC
from typing import List, Tuple

from .. import types


class BaseFormatter(ABC):
    id: str
    name: str

    def __init__(self, id, name):
        self.id = id
        self.name = name

    @abstractmethod
    def export(
        self, show: types.IShow, rundown: types.IRundown, items: List[types.IRundownItem]
    ) -> Tuple[bytes, str, str]:
        pass
