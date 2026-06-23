import logging

from email.message import MIMEPart
from email.utils import formataddr, make_msgid, formatdate
import aiosmtplib
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from superdesk.core import get_current_app, get_config
from superdesk.core.utils import sha
from superdesk.lock import lock, unlock

from .types import (
    EmailMessage,
    EmailConfig,
    EmailAttachment,
    EmailRequest,
    EmailAddress,
)

__all__ = [
    "EmailMessage",
    "EmailConfig",
    "EmailAttachment",
    "EmailRequest",
    "EmailAddress",
    "EmailFactory",
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


def _get_message_from_request(request: EmailRequest) -> EmailMessage:
    msg = EmailMessage()
    msg.set_content(request.text_body)
    msg.add_alternative(request.html_body, subtype="html")
    html_part = _get_html_part_from_message(msg)

    if not html_part:
        raise ValueError("Email message must contain at least one HTML part")

    msg["Subject"] = request.subject.split("\n", 1)[0]
    msg["From"] = sanitize_address(request.sender or get_config(str, "MAIL_DEFAULT_SENDER"))
    msg["To"] = _get_recipient_addresses(request.recipients)
    if request.cc:
        msg["CC"] = _get_recipient_addresses(request.cc)
    if request.bcc:
        msg["BCC"] = _get_recipient_addresses(request.bcc)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()

    if request.attachments:
        for attachment in request.attachments:
            maintype, subtype = attachment.get_content_type().split("/")
            if attachment.cid:
                # If this Attachment has a CID, then we assume it's for embedding into the email
                # So we use `add_related` instead of `add_attachment`.
                # This tells email clients the file is part of the HTML structure, not a separate file to download
                html_part.add_related(
                    attachment.data,
                    maintype=maintype,
                    subtype=subtype,
                    filename=attachment.filename,
                    cid=f"<{attachment.cid}>",
                )
            else:
                msg.add_attachment(
                    attachment.data,
                    maintype=maintype,
                    subtype=subtype,
                    filename=attachment.filename,
                )

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


class EmailFactory:
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

    async def _send(self, client: aiosmtplib.SMTP, request: EmailRequest) -> None:
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
                    logger.error(f"Failed to deliver email: error {code}", extra={"recipient": recipient, "error": msg})
        except aiosmtplib.SMTPAuthenticationError:
            logger.exception("Authentication failed. Check username and password.", extra={"subject": request.subject})
        except aiosmtplib.SMTPServerDisconnected:
            logger.exception("Server unexpectedly disconnected mid-transaction.", extra={"subject": request.subject})
        except aiosmtplib.SMTPException as e:
            logger.exception("A general SMTP error occurred", extra={"subject": request.subject, "error": str(e)})
        except OSError as e:
            logger.exception("OSError while sending email", extra={"subject": request.subject, "error": str(e)})
        finally:
            if lock_id:
                unlock(lock_id, remove=True)

    async def send(self, request: EmailRequest) -> None:
        async with self.get_client() as client:
            await self._send(client, request)

    async def send_bulk_email(self, requests: list[EmailRequest]) -> None:
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
) -> None:
    if get_config(bool, "E2E", False):
        return

    await get_current_app().mail.send(
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
        )
    )
