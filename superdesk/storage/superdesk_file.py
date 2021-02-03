# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2020 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from io import BytesIO
from datetime import datetime

from werkzeug.wsgi import wrap_file
from flask import request, current_app as app

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


def generate_response_for_file(
    file: SuperdeskFile,
    cache_for: int = 3600 * 24 * 30,  # 30d cache
    buffer_size: int = 1024 * 256,
    content_disposition: str = None,
):
    data = wrap_file(request.environ, file, buffer_size=buffer_size)
    response = app.response_class(data, mimetype=file.content_type, direct_passthrough=True)
    response.content_length = file.length
    response.last_modified = file.upload_date
    response.set_etag(file.md5)
    response.cache_control.max_age = cache_for
    response.cache_control.s_max_age = cache_for
    response.cache_control.public = True
    response.make_conditional(request)

    if content_disposition:
        response.headers["Content-Disposition"] = content_disposition
    else:
        filename = "; filename={}".format(file.filename or file.name) if file.filename or file.name else ""
        if strtobool(request.args.get("download", "False")):
            response.headers["Content-Disposition"] = "Attachment" + filename
        else:
            response.headers["Content-Disposition"] = "Inline" + filename

    return response
