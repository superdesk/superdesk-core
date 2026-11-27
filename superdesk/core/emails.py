from typing import cast
import logging

from email.message import MIMEPart, Message
from email.utils import formataddr, make_msgid, formatdate
from mimetypes import guess_type

import aiosmtplib
from quart import has_request_context
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from lxml import etree

from superdesk.core import get_current_app, get_config
from superdesk.core.utils import sha, SingletonInstance
from superdesk.lock import lock, unlock

from .types import (
    EmailMessage,
    EmailConfig,
    EmailAttachment,
    EmailRequest,
    EmailAddress,
    DefaultNoValue,
)

__all__ = [
    "EmailMessage",
    "EmailConfig",
    "EmailAttachment",
    "EmailRequest",
    "EmailAddress",
    "EmailFactory",
    "send_email_async",
    "send_email",
]


logger = logging.getLogger(__name__)


def sanitize_address(address: EmailAddress) -> str:
    return address if isinstance(address, str) else formataddr(address)


def _get_html_part_from_message(message: EmailMessage) -> MIMEPart | None:
    for part in message.iter_parts():
        if part.get_content_type() == "text/html":
            return part

    return None


def _get_recipient_addresses(recipients: list[EmailAddress]) -> str:
    return ", ".join([sanitize_address(recipient) for recipient in recipients])


def _get_attachment_content_type(attachment: EmailAttachment) -> str:
    content_type = attachment.content_type
    if content_type is None and attachment.filename is not None:
        content_type = guess_type(attachment.filename)[0]

    if content_type is None:
        if isinstance(attachment.data, str):
            content_type = "text/plain"
        else:
            content_type = "application/octet-stream"

    return content_type


MAX_LINE_LENGTH = 998 - 50  # RFC 5322 - buffer for html indentation


def handle_long_lines_text(text, limit=MAX_LINE_LENGTH):
    if not text:
        return ""
    output = []
    lines = text.splitlines()
    for line in lines:
        if len(line) < limit:
            output.append(line)
        else:
            next_line = ""
            words = line.split()
            for word in words:
                if len(next_line) + len(word) > limit:
                    output.append(next_line)
                    next_line = word
                else:
                    next_line += (" " if len(next_line) else "") + word

            if next_line:
                output.append(next_line)
    return "\n".join(output)


def handle_long_lines_html(html):
    lines = html.splitlines()
    if not any([len(line) > MAX_LINE_LENGTH for line in lines]):
        return html
    parsed = etree.fromstring(html, parser=etree.HTMLParser())
    etree.indent(parsed, space=" ")  # like pretty print but upfront
    for elem in parsed.iter("*"):
        if elem.text is not None and len(elem.text) > 100:
            elem.text = handle_long_lines_text(elem.text, 100) + "\n"
        if elem.tail is not None and len(elem.tail) > 100:
            elem.tail = handle_long_lines_text(elem.tail, 100) + "\n"
    return etree.tostring(parsed, method="html", encoding="unicode")


def _get_message_from_request(request: EmailRequest) -> EmailMessage:
    msg = EmailMessage()
    msg.set_content(handle_long_lines_text(request.text_body))

    msg["Subject"] = request.subject.split("\n", 1)[0].strip()
    msg["From"] = sanitize_address(request.sender or get_config(str, "MAIL_DEFAULT_SENDER"))
    msg["To"] = _get_recipient_addresses(request.recipients)
    if request.cc:
        msg["CC"] = _get_recipient_addresses(request.cc)
    if request.bcc:
        msg["BCC"] = _get_recipient_addresses(request.bcc)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()

    if not request.html_body and not request.attachments:
        # This is a text only email without attachments
        # we can send the message now
        return msg

    html_part: MIMEPart | None = None
    if request.html_body:
        msg.add_alternative(handle_long_lines_html(request.html_body), subtype="html")
        html_part = _get_html_part_from_message(msg)

        if not html_part:
            raise ValueError("Failed to add html_body to email request")

    if not request.attachments:
        # This is a text & html email without attachments
        # we can send the message now
        return msg

    # We have attachments, make sure to add them to the appropriate part of the email request
    target_container: MIMEPart
    for attachment in request.attachments:
        maintype, subtype = _get_attachment_content_type(attachment).split("/")

        # Encode str payloads to bytes: a str routes to set_text_content() which rejects
        # maintype/subtype and raises a TypeError; bytes routes to set_bytes_content() (base64).
        data = attachment.data.encode("utf-8") if isinstance(attachment.data, str) else attachment.data

        attachment_kwargs: dict = dict(
            maintype=maintype,
            subtype=subtype,
            filename=attachment.filename,
        )
        if attachment.headers:
            attachment_kwargs["headers"] = attachment.headers

        if attachment.cid:
            # If this Attachment has a CID, then we assume it's for embedding into the email
            # So we use `add_related` instead of `add_attachment`.
            # This tells email clients the file is part of the HTML structure, not a separate file to download
            if not html_part:
                raise ValueError("Unable to add attachment, html_body not found in email request")

            html_part.add_related(data, cid=f"<{attachment.cid}>", **attachment_kwargs)
            target_container = html_part
        else:
            msg.add_attachment(data, **attachment_kwargs)
            target_container = msg

        if attachment.description:
            payload = target_container.get_payload()
            if isinstance(payload, list) and payload:
                last_part = payload[-1]
                if isinstance(last_part, Message):
                    last_part["Content-Description"] = attachment.description

    return msg


def _get_request_hash(request: EmailRequest) -> str:
    return sha(
        dict(
            subject=request.subject,
            recipients=request.recipients,
            text_body=request.text_body,
            html_body=request.html_body,
            cc=request.cc,
            bcc=request.bcc,
        )
    )


def _get_config() -> EmailConfig:
    return EmailConfig.create_from_dict(get_current_app().config, prefix="MAIL", freeze=True)


class EmailFactory(SingletonInstance):
    @classmethod
    def _get_instance(cls) -> "EmailFactory | None":
        try:
            app = get_current_app()
            return cast(EmailFactory, app.mail)
        except RuntimeError:
            pass

        return None

    @classmethod
    def _set_instance(cls, instance: "EmailFactory") -> None:
        try:
            app = get_current_app()
            app.mail = instance
        except RuntimeError:
            pass

    def get_client(self):
        config = _get_config()
        return aiosmtplib.SMTP(
            hostname=config.server,
            port=config.port,
            timeout=config.timeout,
            use_tls=config.use_tls,
            start_tls=config.start_tls,
            username=None if not config.username else config.username,
            password=None if not config.password else config.password,
        )

    def get_address(self, sender: str | None, sender_name: str | None) -> EmailAddress | None:
        if not sender:
            return None
        elif sender_name:
            return sender, sender_name
        else:
            return sender

    async def _send(self, client: aiosmtplib.SMTP, request: EmailRequest, raise_exceptions: bool = False) -> None:
        lock_id = f"email:{_get_request_hash(request)}" if request.use_lock else None
        if lock_id and not lock(lock_id, expire=120):
            logger.error(
                "Lock for this email request already exists, skipping",
                extra={"subject": request.subject, "lock_id": lock_id},
            )
            return

        try:
            errors, response_message = await client.send_message(_get_message_from_request(request))

            if errors:
                for recipient, error_details in errors.items():
                    code, msg = error_details
                    if raise_exceptions and 500 <= int(code) <= 599:
                        raise aiosmtplib.SMTPResponseException(code, msg)
                    logger.error(f"Failed to deliver email: error {code}", extra={"recipient": recipient, "error": msg})
        except aiosmtplib.SMTPAuthenticationError:
            logger.exception("Authentication failed. Check username and password.", extra={"subject": request.subject})
            if raise_exceptions:
                raise
        except aiosmtplib.SMTPServerDisconnected:
            logger.exception("Server unexpectedly disconnected mid-transaction.", extra={"subject": request.subject})
            if raise_exceptions:
                raise
        except aiosmtplib.SMTPException as e:
            logger.exception("A general SMTP error occurred", extra={"subject": request.subject, "error": str(e)})
            if raise_exceptions:
                raise
        except OSError as e:
            logger.exception("OSError while sending email", extra={"subject": request.subject, "error": str(e)})
            if raise_exceptions:
                raise
        finally:
            if lock_id:
                unlock(lock_id, remove=True)

    def _use_celery_for_request(self, request: EmailRequest) -> bool:
        if request.use_celery is False:
            return False

        config = _get_config()
        use_celery = config.use_celery if request.use_celery is DefaultNoValue else request.use_celery
        return use_celery is True or (use_celery is None and has_request_context())

    async def send(self, request: EmailRequest, raise_exceptions: bool = False) -> None:
        if self._use_celery_for_request(request):
            await send_email_pydantic.delay(request.to_dict(mode="json"), raise_exceptions)
        else:
            async with self.get_client() as client:
                await self._send(client, request, raise_exceptions)

    async def send_bulk_email(self, requests: list[EmailRequest], raise_exceptions: bool = False) -> None:
        if not len(requests):
            return

        # Use the 1st request in the bulk request to provide `use_celery` value
        if self._use_celery_for_request(requests[0]):
            for request in requests:
                await send_email_pydantic.delay(request.to_dict(mode="json"), raise_exceptions)
        else:
            async with self.get_client() as client:
                for request in requests:
                    # As SMTP is a sequential protocol, we can't send multiple emails in parallel with the 1 connection
                    # If parallel sending is required, consider using multiple connections
                    # or send multiple celery tasks (so they're picked up by different workers)
                    await self._send(client, request)


SMTP_RETRY_ERRORS = (
    aiosmtplib.SMTPTimeoutError,
    aiosmtplib.SMTPConnectError,
    aiosmtplib.SMTPException,
    SoftTimeLimitExceeded,
)


async def send_email_async(
    subject: str,
    sender: EmailAddress,
    recipients: list[EmailAddress],
    text_body: str,
    html_body: str,
    cc: list[EmailAddress] | None = None,
    bcc: list[EmailAddress] | None = None,
    attachments: list[EmailAttachment] | None = None,
    use_lock: bool = True,
    raise_exceptions: bool = False,
) -> None:
    if get_config(bool, "E2E", False):
        return

    await EmailFactory().send(
        EmailRequest(
            subject=subject,
            sender=sender,
            recipients=recipients,
            text_body=text_body,
            html_body=html_body,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
            use_lock=use_lock,
        ),
        raise_exceptions=raise_exceptions,
    )


@shared_task(
    name="superdesk.core.emails.send",
    autoretry_for=SMTP_RETRY_ERRORS,
    max_retries=3,
    retry_backoff=True,  # Safely spaces retries (e.g., 2s, 4s, 8s)
    retry_jitter=True,
    soft_time_limit=120,
)
async def send_email_pydantic(request_dict: dict, raise_exceptions: bool = False) -> None:
    request = EmailRequest.from_dict(request_dict)
    # Make sure we're sending the email in the current asyncio event loop
    request.use_celery = False
    await EmailFactory().send(request, raise_exceptions)


@shared_task(
    autoretry_for=SMTP_RETRY_ERRORS,
    max_retries=3,
    retry_backoff=True,  # Safely spaces retries (e.g., 2s, 4s, 8s)
    retry_jitter=True,
    soft_time_limit=120,
)
async def send_email(
    subject: str,
    sender: EmailAddress,
    recipients: list[EmailAddress],
    text_body: str,
    html_body: str,
    cc: list[EmailAddress] | None = None,
    bcc: list[EmailAddress] | None = None,
    attachments: list[EmailAttachment] | None = None,
    use_lock: bool = True,
    raise_exceptions: bool = False,
) -> None:
    await send_email_async(
        subject=subject,
        sender=sender,
        recipients=recipients,
        text_body=text_body,
        html_body=html_body,
        cc=cc,
        bcc=bcc,
        attachments=attachments,
        use_lock=use_lock,
        raise_exceptions=raise_exceptions,
    )
