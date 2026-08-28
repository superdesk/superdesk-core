from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..errors import AIProviderError


@dataclass
class CompletionMessage:
    role: str
    content: str


@dataclass
class CompletionRequest:
    model: str
    messages: list[CompletionMessage]
    temperature: float = 0.7
    json_mode: bool = False
    max_tokens: int | None = None


@dataclass
class CompletionResult:
    content: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw_usage: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionTestResult:
    ok: bool
    models_count: int = 0
    error: str | None = None


class AIProviderClient(ABC):
    """Interface implemented by every AI provider type.

    A client is built from a stored ``AIProvider`` and lives for the duration of one operation,
    so it must not cache anything between calls.
    """

    def __init__(self, base_url: str, api_key: str | None = None, config: dict[str, Any] | None = None) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.config = config or {}

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResult:
        """Run a single completion and return its text

        :raises AIProviderError: If the provider cannot be reached or answers with an unusable body
        """

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Return the ids of the models the provider offers

        :raises AIProviderError: If the provider cannot be reached or answers with an unusable body
        """

    async def test_connection(self) -> ConnectionTestResult:
        """Report whether the provider answers with its model list, without raising"""

        try:
            models = await self.list_models()
        except AIProviderError as error:
            return ConnectionTestResult(ok=False, error=error.message)

        return ConnectionTestResult(ok=True, models_count=len(models))
