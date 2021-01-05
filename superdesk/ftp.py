import socket
import ftplib

from contextlib import contextmanager
from flask import current_app as app

from superdesk.errors import IngestFtpError


@contextmanager
def ftp_connect(config):
    """Get ftp connection for given config.

    use with `with`

    :param config: dict with `host`, `username`, `password`, `path`, `passive` and `use_ftp`
    """
    if config.get("use_ftps", False):
        try:
            ftp = ftplib.FTP_TLS(config.get("host"), timeout=app.config.get("FTP_TIMEOUT", 300))
        except socket.gaierror as e:
            raise IngestFtpError.ftpHostError(exception=e)

        try:
            ftp.auth()
        except ftplib.error_perm as ae:
            ftp.close()
            raise IngestFtpError.ftpAuthError(exception=ae)
    else:
        try:
            ftp = ftplib.FTP(config.get("host"), timeout=app.config.get("FTP_TIMEOUT", 300))
        except socket.gaierror as e:
            raise IngestFtpError.ftpHostError(exception=e)

    if config.get("username"):
        try:
            ftp.login(config.get("username"), config.get("password"))
        except ftplib.error_perm as e:
            raise IngestFtpError.ftpAuthError(exception=e)

    # set encryption on data channel if able
    if hasattr(ftp, "prot_p"):
        ftp.prot_p()

    if config.get("path"):
        ftp.cwd(config.get("path", "").lstrip("/"))
    if config.get("passive") is False:  # only set this when not active, it's passive by default
        ftp.set_pasv(False)
    yield ftp
    ftp.close()
