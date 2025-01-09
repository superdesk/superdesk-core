from typing import cast
from dataclasses import dataclass
from quart_babel.speaklater import LazyString


@dataclass(frozen=True)
class Privilege:
    name: str
    label: LazyString | None = None
    category: LazyString | None = None
    description: LazyString | None = None


class PrivilegesRegistry:
    __privileges: set[Privilege] | frozenset[Privilege] = set()

    def add(self, privilege: Privilege):
        """Add a privilege if the registry is not locked."""

        if self.is_locked:
            raise RuntimeError("Cannot add privileges after the app has started.")

        # mypy does not pick the `is_locked` condition
        self.__privileges = cast(set[Privilege], self.__privileges)
        self.__privileges.add(privilege)

    @property
    def is_locked(self):
        return isinstance(self.__privileges, frozenset)

    def lock(self):
        """Lock the registry by converting the privileges to a frozenset."""

        if not self.is_locked:
            self.__privileges = frozenset(self.__privileges)

    def get_all(self) -> list[Privilege]:
        """Retrieve all privileges."""

        return list(self.__privileges)

    def __contains__(self, name: str) -> bool:
        """Check if a privilege exists."""

        return any(priv.name == name for priv in self.__privileges)
