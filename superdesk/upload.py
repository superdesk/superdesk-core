# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Upload module"""
import logging

from eve.utils import config
from flask import request, current_app as app, redirect, make_response, jsonify

import superdesk
import json
import os
from superdesk.errors import SuperdeskApiError
from superdesk.media.renditions import generate_renditions, delete_file_on_error
from superdesk.media.media_operations import (
    download_file_from_url,
    download_file_from_encoded_str,
    process_file_from_stream,
    crop_image,
    decode_metadata,
)
from superdesk.filemeta import set_filemeta
from superdesk.storage.superdesk_file import generate_response_for_file
from superdesk.users.services import current_user_has_privilege
from superdesk.auth.decorator import blueprint_auth
from superdesk import get_resource_privileges
from .resource import Resource
from .services import BaseService


bp = superdesk.Blueprint("upload_raw", __name__)
logger = logging.getLogger(__name__)


@bp.route("/upload/<path:media_id>/raw", methods=["GET"])
@blueprint_auth()
def get_upload_as_data_uri_bc(media_id):
    """Keep previous url for backward compatibility"""
    return redirect(upload_url(media_id))


@bp.route("/upload-raw/<path:media_id>", methods=["GET"])
@blueprint_auth()
def get_upload_as_data_uri(media_id):
    if not request.args.get("resource"):
        media_file = app.media.get_by_filename(media_id)
    else:
        media_file = app.media.get(media_id, request.args["resource"])
    if media_file:
        return generate_response_for_file(media_file)

    raise SuperdeskApiError.notFoundError("File not found on media storage.")


@bp.route("/upload/config-file", methods=["POST", "OPTIONS"])
@blueprint_auth()
def upload_config_file():
    if request.method == "OPTIONS":
        # return headers to avoid CORS problems
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "POST")
        return response

    _resource = request.args.get("resource")
    if not _resource:
        raise SuperdeskApiError.forbiddenError("Provide required param: 'resource'.")

    resource_privileges = get_resource_privileges(_resource).get("POST", None)
    if not current_user_has_privilege(resource_privileges):
        raise SuperdeskApiError.forbiddenError("You don't have permissions to upload JSON file.")

    json_files = request.files.getlist("json_file")
    if not json_files:
        raise SuperdeskApiError.badRequestError("Provide JSON file with key 'json_file'.")

    _items = []
    for _file in json_files:
        file_name = _file.filename
        _, ext = os.path.splitext(file_name)
        if ext not in [".json"]:
            raise SuperdeskApiError.badRequestError(
                "File is not allowed: {}, Only JSON file is allowed to upload.".format(file_name)
            )

        try:
            file_data = json.loads(_file.read())
        except Exception as ex:
            logger.error("Invalid JSON file {0}: {1}".format(file_name, str(ex)))
            raise SuperdeskApiError.internalError("Invalid JSON file: {}.".format(file_name))

        if type(file_data) == dict:
            file_data = [file_data]
        _items += file_data

    res = superdesk.get_resource_service(_resource).update_data_from_json(_items)
    response = make_response(jsonify(res))
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Expose-Headers", "*")
    return response


def url_for_media(media_id, mimetype=None):
    return app.media.url_for_media(media_id, mimetype)


def upload_url(media_id, view="upload_raw.get_upload_as_data_uri"):
    media_prefix = app.config.get("MEDIA_PREFIX").rstrip("/")
    return "%s/%s" % (media_prefix, media_id)


def init_app(app) -> None:
    endpoint_name = "upload"
    service = UploadService(endpoint_name, backend=superdesk.get_backend())
    UploadResource(endpoint_name, app=app, service=service)
    superdesk.blueprint(bp, app)
    app.upload_url = upload_url

    # Using intrinsic privilege so that any user can update their profile Avatar
    # This still restricts this endpoint to logged in users only
    superdesk.intrinsic_privilege(resource_name="upload", method=["POST"])


class UploadResource(Resource):
    schema = {
        "media": {"type": "file"},
        "CropLeft": {"type": "integer"},
        "CropRight": {"type": "integer"},
        "CropTop": {"type": "integer"},
        "CropBottom": {"type": "integer"},
        "URL": {"type": "string"},
        "mimetype": {"type": "string"},
        "filemeta": {"type": "dict"},
        "filemeta_json": {"type": "string"},
    }
    extra_response_fields = ["renditions"]
    datasource = {
        "projection": {
            "mimetype": 1,
            "filemeta": 1,
            "_created": 1,
            "_updated": 1,
            "_etag": 1,
            "media": 1,
            "renditions": 1,
            "filemeta_json": 1,
        }
    }
    item_methods = ["GET", "DELETE"]
    resource_methods = ["GET", "POST"]
    privileges = {"DELETE": "archive"}


class UploadService(BaseService):
    def on_create(self, docs):
        for doc in docs:
            if doc.get("URL") and doc.get("media"):
                message = "Uploading file by URL and file stream in the same time is not supported."
                raise SuperdeskApiError.badRequestError(message)

            content = None
            filename = None
            content_type = None
            if doc.get("media"):
                content = doc["media"]
                filename = content.filename
                content_type = content.mimetype
            elif doc.get("URL"):
                content, filename, content_type = self.download_file(doc)

            self.crop_and_store_file(doc, content, filename, content_type)

    def crop_and_store_file(self, doc, content, filename, content_type):
        # retrieve file name and metadata from file
        file_name, content_type, metadata = process_file_from_stream(content, content_type=content_type)
        # crop the file if needed, can change the image size
        was_cropped, out = crop_image(content, filename, doc)
        # the length in metadata could be updated if it was cropped
        if was_cropped:
            file_name, content_type, metadata_after_cropped = process_file_from_stream(out, content_type=content_type)
            # when cropped, metadata are reseted. Then we update the previous metadata variable
            metadata["length"] = metadata_after_cropped["length"]
        try:
            logger.debug("Going to save media file with %s " % file_name)
            out.seek(0)
            file_id = app.media.put(
                out, filename=file_name, content_type=content_type, resource=self.datasource, metadata=metadata
            )
            doc["media"] = file_id
            doc["mimetype"] = content_type
            set_filemeta(doc, decode_metadata(metadata))
            inserted = [doc["media"]]
            file_type = content_type.split("/")[0]
            rendition_spec = config.RENDITIONS["avatar"]
            renditions = generate_renditions(
                out, file_id, inserted, file_type, content_type, rendition_spec, url_for_media
            )
            doc["renditions"] = renditions
        except Exception as io:
            for file_id in inserted:
                delete_file_on_error(doc, file_id)
            raise SuperdeskApiError.internalError("Generating renditions failed", exception=io)

    def download_file(self, doc):
        url = doc.get("URL")
        if not url:
            return
        if url.startswith("data"):
            return download_file_from_encoded_str(url)
        else:
            return download_file_from_url(url)
