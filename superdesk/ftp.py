
import ftplib

from contextlib import contextmanager
from flask import current_app as app


@contextmanager
def ftp_connect(config):
    """Get ftp connection for given config.

    use with `with`

    :param config: dict with `host`, `username`, `password`, `path` and `passive`
    """
    ftp = ftplib.FTP(config.get('host'), timeout=app.config.get('FTP_TIMEOUT', 300))
    if config.get('username'):
        ftp.login(config.get('username'), config.get('password'))
    if config.get('path'):
        ftp.cwd(config.get('path', '').lstrip('/'))
    if config.get('passive') is False:  # only set this when not active, it's passive by default
        ftp.set_pasv(False)
    yield ftp
    ftp.close()
