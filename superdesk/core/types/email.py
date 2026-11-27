from typing import TypeAlias, Protocol
import email.policy
from email.message import EmailMessage as BaseEmailMessage

from pydantic import ConfigDict

from ..config import ConfigModel
from .model import BaseModel
from .common import DefaultNoValue

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
        return body_part.get_content().strip() if body_part else None


class EmailConfig(ConfigModel):
    server: str = "localhost"
    port: int = 25
    use_tls: bool = False
    start_tls: bool | None = None
    username: str = ""
    password: str = ""
    timeout: int = 60
    default_sender: str = "superdesk@localhost"

    #: True: Send all emails using celery tasks
    #: False: Send all emails in current asyncio event loop
    #: None: Send email using celery, if inside Quart context, otherwise sends in current asyncio event loop
    use_celery: bool | None = None


class EmailAttachment(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        val_json_bytes="base64",  # Decodes incoming Base64 JSON `data` to bytes
        ser_json_bytes="base64",  # Serializes `data` to URL-safe Base64 JSON strings
        arbitrary_types_allowed=True,
        validate_assignment=True,  # Revalidate on field assignment
        populate_by_name=True,
        revalidate_instances="always",
        extra="allow",  # Allow any fields not defined in the ResourceModel/dataclass
        protected_namespaces=(),
    )

    data: str | bytes
    content_type: str | None = None
    filename: str | None = None
    disposition: str = "attachment"
    cid: str | None = None
    description: str | None = None
    headers: dict | None = None


class EmailRequest(BaseModel):
    subject: str
    recipients: list[EmailAddress]
    text_body: str
    html_body: str | None = None
    sender: EmailAddress | None = None  # Defaults to ``EmailConfig.default_sender``
    cc: list[EmailAddress] | None = None
    bcc: list[EmailAddress] | None = None
    attachments: list[EmailAttachment] | None = None
    use_lock: bool = True
    use_celery: bool | None | object = DefaultNoValue


class EmailFactoryProtocol(Protocol):
    async def send(self, request: EmailRequest, raise_exceptions: bool = False) -> None:
        ...

    async def send_bulk_email(self, requests: list[EmailRequest], raise_exceptions: bool = False) -> None:
        ...
