from typing import TypeAlias, Protocol
from dataclasses import dataclass
import email.policy
from email.message import EmailMessage as BaseEmailMessage
from mimetypes import guess_type

from ..config import ConfigModel
from .model import BaseModel

__all__ = [
    "EmailMessage",
    "EmailConfig",
    "EmailAddress",
    "EmailAttachment",
    "EmailRequest",
]

EmailAddress: TypeAlias = str | tuple[str, str]


class EmailMessage(BaseEmailMessage):
    def as_bytes(self, unixfrom=False, policy=None):
        return super().as_bytes(policy=email.policy.HTTP)

    @property
    def subject(self) -> str:
        return self["Subject"]

    @property
    def body(self) -> str | None:
        body_part = self.get_body(preferencelist=("plain",))
        return body_part.get_content() if body_part else None

    @property
    def html(self) -> str | None:
        body_part = self.get_body(preferencelist=("html",))
        return body_part.get_content() if body_part else None


class EmailConfig(ConfigModel):
    server: str = "localhost"
    port: int = 25
    use_tls: bool = False
    start_tls: bool | None = None
    username: str = ""
    password: str = ""
    timeout: int = 60
    default_sender: str = "superdesk@localhost"


class EmailAttachment(BaseModel):
    data: str | bytes
    content_type: str | None = None
    filename: str | None = None
    disposition: str = "attachment"
    cid: str | None = None

    def get_content_type(self) -> str:
        content_type = self.content_type
        if content_type is None and self.filename is not None:
            content_type = guess_type(self.filename)[0]

        if content_type is None:
            if isinstance(self.data, str):
                content_type = "text/plain"
            else:
                content_type = "application/octet-stream"

        return content_type


class EmailRequest(BaseModel):
    subject: str
    recipients: list[EmailAddress]
    text_body: str
    html_body: str
    sender: EmailAddress | None = None  # Defaults to ``EmailConfig.default_sender``
    cc: list[EmailAddress] | None = None
    bcc: list[EmailAddress] | None = None
    attachments: list[EmailAttachment] | None = None
    use_lock: bool = True


class EmailFactoryProtocol(Protocol):
    async def send(self, request: EmailRequest, raise_exceptions: bool = False) -> None:
        ...

    async def send_bulk_email(self, requests: list[EmailRequest]) -> None:
        ...
