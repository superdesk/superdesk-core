
import socket
import ftplib

from contextlib import contextmanager
from flask import current_app as app

from superdesk.errors import IngestFtpError


@contextmanager
def ftp_connect(config):
    """Get ftp connection for given config.

    use with `with`

    :param config: dict with `host`, `username`, `password`, `path` and `passive`
    """
    try:
        ftp = ftplib.FTP(config.get('host'), timeout=app.config.get('FTP_TIMEOUT', 300))
    except socket.gaierror as e:
        raise IngestFtpError.ftpHostError(exception=e)
    if config.get('username'):
        try:
            ftp.login(config.get('username'), config.get('password'))
        except ftplib.error_perm as e:
            raise IngestFtpError.ftpAuthError(exception=e)
    if config.get('path'):
        ftp.cwd(config.get('path', '').lstrip('/'))
    if config.get('passive') is False:  # only set this when not active, it's passive by default
        ftp.set_pasv(False)
    yield ftp
    ftp.close()
