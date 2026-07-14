import asyncio
import socket
import ssl
import logging
from collections.abc import AsyncIterator, AsyncGenerator
from io import BytesIO

import aioftp

from contextlib import asynccontextmanager
from superdesk.core import get_app_config
from superdesk.core.types import SuperdeskAsyncFile
from superdesk.errors import IngestFtpError


logger = logging.getLogger(__name__)
all_ftp_errors = (
    # aioftp-specific errors
    aioftp.AIOFTPException,
    # Timeout while connecting/reading/writing
    asyncio.TimeoutError,
    TimeoutError,
    # DNS/host resolution error
    socket.gaierror,
    # TCP connection issues
    ConnectionRefusedError,
    ConnectionResetError,
    BrokenPipeError,
    # FTPS/TLS errors
    ssl.SSLError,
    # Other socket/OS-level errors
    OSError,
)


class FTPClient(aioftp.Client):
    async def upload_data(
        self, filename: str, data: SuperdeskAsyncFile | AsyncGenerator[bytes, None] | BytesIO | bytes
    ):
        if isinstance(data, (AsyncGenerator, SuperdeskAsyncFile)):
            async with self.upload_stream(filename) as stream:
                async for chunk in data:
                    await stream.write(chunk)
        elif isinstance(data, bytes):
            async with self.upload_stream(filename) as stream:
                await stream.write(data)
        elif isinstance(data, BytesIO):
            data.seek(0)
            async with self.upload_stream(filename) as stream:
                await stream.write(data.read())
        else:
            raise TypeError("Invalid data type for upload")


@asynccontextmanager
async def ftp_connect(config) -> AsyncIterator[FTPClient]:
    """Get ftp connection for given config.

    use with `with`

    :param config: dict with `host`, `username`, `password`, `path`, `passive` and `use_ftp`
    """

    host = config.get("host")
    timeout = get_app_config("FTP_TIMEOUT", 300)
    use_ftps = config.get("use_ftps", False)

    ftp_kwargs = dict(
        socket_timeout=timeout,
        connection_timeout=timeout,
        upgrade_to_tls=use_ftps,
        ssl=use_ftps,
    )

    if config.get("username"):
        ftp_kwargs["user"] = config["username"]
    if config.get("password"):
        ftp_kwargs["password"] = config["password"]

    try:
        async with FTPClient.context(host, **ftp_kwargs) as client:
            if config.get("path"):
                await client.change_directory(config["path"].lstrip("/"))

            yield client
    except aioftp.StatusCodeError as ex:
        # FTP server replied with an error status code.
        received_code = getattr(ex, "received_code", None)

        if received_code in {"332", "430", "530"}:
            raise await IngestFtpError.ftpAuthError(exception=ex).send_notifications()

        raise await IngestFtpError.ftpError(exception=ex).send_notifications()
    except aioftp.AIOFTPException as ex:
        # aioftp-specific connection/data-channel condition failure.
        raise await IngestFtpError.ftpError(exception=ex).send_notifications()
    except (asyncio.TimeoutError, TimeoutError) as ex:
        # Connect/read/write/path timeout.
        raise await IngestFtpError.ftpTimeoutError(exception=ex).send_notifications()
    except socket.gaierror as ex:
        # DNS/host resolution failed.
        raise await IngestFtpError.ftpHostError(exception=ex).send_notifications()
    except (ConnectionRefusedError, ConnectionResetError, BrokenPipeError) as ex:
        # TCP connection refused, reset, or broken while transferring.
        raise await IngestFtpError.ftpHostError(exception=ex).send_notifications()
    except ssl.SSLError as ex:
        # FTPS/TLS negotiation or certificate problem.
        raise await IngestFtpError.ftpSSLError(exception=ex).send_notifications()
    except OSError as ex:
        # Other network/socket-level failures.
        raise await IngestFtpError.ftpError(exception=ex).send_notifications()
    except asyncio.CancelledError as ex:
        # Important: do not swallow task cancellation.
        logger.exception(ex)
        raise
