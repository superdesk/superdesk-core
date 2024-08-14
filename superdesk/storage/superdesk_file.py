# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2020 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Optional
from io import BytesIO
from datetime import datetime, timezone, timedelta

from werkzeug.wsgi import wrap_file, FileWrapper

from superdesk.core import get_current_app
from superdesk.flask import request
from superdesk.default_settings import strtobool


class SuperdeskFile(BytesIO):
    _name: str
    filename: str
    content_type: str
    length: int
    upload_date: datetime
    md5: str

    @property
    def name(self):
        return self._name


async def generate_response_for_file(
    file: SuperdeskFile,
    cache_for: int = 3600 * 24 * 30,  # 30d cache
    buffer_size: int = 1024 * 256,
    content_disposition: Optional[str] = None,
):
    app = get_current_app()
    # file_body = FileWrapper(file, buffer_size)

    from quart.wrappers.response import IOBody

    print(app.as_any().response_class.io_body_class)
    print(app.as_any().response_class.io_body_class.__name__)
    print(app.as_any().response_class.io_body_class.__class__)
    file_body = app.as_any().response_class.io_body_class(file, buffer_size=buffer_size)
    response = app.response_class(file_body, mimetype=file.content_type)
    response.content_length = file.length
    response.last_modified = file.upload_date
    response.set_etag(file.md5)
    response.cache_control.max_age = cache_for
    response.cache_control.s_max_age = cache_for
    response.cache_control.public = True
    response.expires = datetime.now(timezone.utc) + timedelta(seconds=cache_for)

    # Add ``accept_ranges`` & ``complete_length`` so video seeking is supported
    await response.make_conditional(request, accept_ranges=True, complete_length=file.length)

    if content_disposition:
        response.headers["Content-Disposition"] = content_disposition
    else:
        filename = "; filename={}".format(file.filename or file.name) if file.filename or file.name else ""
        if strtobool(request.args.get("download", "False")):
            response.headers["Content-Disposition"] = "Attachment" + filename
        else:
            response.headers["Content-Disposition"] = "Inline" + filename

    return response
