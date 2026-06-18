from typing import TypeAlias
from unittest.mock import patch
from contextlib import contextmanager

from aiosmtplib import SMTP
from aiosmtplib.response import SMTPResponse

from superdesk.core.emails import EmailMessage, EmailFactory


RecordedEmail: TypeAlias = tuple[str, list[str], EmailMessage]


class MockEmailFactory(EmailFactory):
    messages: list[EmailMessage] = []

    @contextmanager
    def record_messages(self):
        self.messages.clear()
        yield self.messages

    def get_client(self, *args, **kwargs):
        return MockSMTP(
            self.messages,
            *args,
            **kwargs,
        )


class MockSMTP(SMTP):
    messages: list[EmailMessage]

    def __init__(self, messages: list[EmailMessage], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messages = messages

        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def connect(self, *args, **kwargs) -> SMTPResponse:
        self._is_connected = True
        return SMTPResponse(220, "://example.com ESMTP Server Ready (mocked)")

    async def quit(self, *args, **kwargs) -> SMTPResponse:
        self._is_connected = False
        return SMTPResponse(221, "2.0.0 Bye (mocked)")

    def close(self) -> None:
        self._is_connected = False

    # --- 2. Authentication Mocking (If your code calls login()) ---
    async def login(self, *args, **kwargs) -> SMTPResponse:
        return SMTPResponse(235, "2.7.0 Authentication successful (mocked)")

    # --- 3. Async Context Manager Lifecycle Overrides ---
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._is_connected:
            await self.quit()

    async def send_message(  # type: ignore[override]
        self,
        message: EmailMessage,
        sender: str | None = None,
        recipients: list[str] | None = None,
        **kwargs,
    ) -> tuple[dict[str, SMTPResponse], str]:
        # Intercept and record the message before/after sending
        # self.messages.append((sender or "", recipients or [], message))
        self.messages.append(message)

        # Return a dummy tuple mimicking a successful SMTP send response
        # (aiosmtplib.send_message usually returns a tuple of (recipients, response_string))
        return {}, "250 Message accepted for delivery (mocked)"
