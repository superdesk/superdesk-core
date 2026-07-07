# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.eve_async.service import AsyncBaseService
from superdesk.resource_fields import ID_FIELD
from superdesk.resource import Resource
from superdesk.media.renditions import generate_renditions, get_renditions_spec_async
from superdesk.celery_app.task_result import AsyncTaskResult
from superdesk import get_resource_service
from superdesk import errors
from superdesk.core import get_current_app

from PIL import Image, ImageEnhance
from io import BytesIO
import os.path
import uuid
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


def transform(im, operation):
    """Apply image transformation

    :param Image im: image to transform
    :param str operation: name of the operation to do
    :param param: parameters of the operation
    :return Image: resulting image
    """
    operation_type = operation[0]
    param = operation[1]

    if operation_type == "rotate":
        return im.rotate(int(param), expand=1)

    elif operation_type == "flip":
        if param in ("vertical", "both"):
            im = im.transpose(Image.FLIP_TOP_BOTTOM)
        if param in ("horizontal", "both"):
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        return im

    elif operation_type == "brightness":
        return ImageEnhance.Brightness(im).enhance(float(param))

    elif operation_type == "contrast":
        return ImageEnhance.Contrast(im).enhance(float(param))

    elif operation_type == "grayscale":
        return im.convert("L")

    elif operation_type == "saturation":
        return ImageEnhance.Color(im).enhance(float(param))

    logger.warning("unhandled operation: {operation} {param}".format(operation=operation_type, param=param))

    return im


@shared_task(store_async_result=True)
async def perform_operations_in_celery(rendition: dict, operations: list[tuple[str, str | int | float]]):
    app = get_current_app()
    media_id = rendition["media"]
    media = app.media.get(media_id)
    out = im = Image.open(media)

    # we apply all requested operations on original media
    for operation in operations:
        try:
            out = transform(out, operation)
        except ValueError:
            # if the operation can't be applied just ignore it
            logger.warning(
                "failed to apply operation: {operation} {param} for media {id}".format(
                    operation=operation[0], param=operation[1], id=media_id
                )
            )

    buf = BytesIO()
    out.save(buf, format=im.format)

    # we set metadata
    buf.seek(0)
    content_type = rendition["mimetype"]
    ext = os.path.splitext(rendition["href"])[1]
    filename = str(uuid.uuid4()) + ext

    # and save transformed media in database
    media_id = await app.media.put_async(buf, filename=filename, content_type=content_type)

    renditions = generate_renditions(
        buf, media_id, [], "image", content_type, await get_renditions_spec_async(), app.media.url_for_media
    )

    return renditions


class MediaEditorResource(Resource):
    schema = {
        "item_id": {
            "type": "string",
        },
        "item": {
            "type": "dict",
        },
        "edit": {
            "type": "list",
            "required": True,
        },
        "renditions": {
            "type": "dict",
        },
    }
    internal_resource = False
    resource_methods = ["POST"]
    item_methods = []
    privileges = {"POST": "archive"}


class MediaEditorService(AsyncBaseService):
    """Service givin metadata on backend itself"""

    async def create_async(self, docs: list[dict], **kwargs) -> list:
        """Apply transformation requested in 'edit'"""
        ids = []
        archive = get_resource_service("archive")
        for doc in docs:
            # first we get item and requested edit operations
            item = doc.pop("item", None)
            if item is None:
                try:
                    item_id = doc.pop("item_id")
                except KeyError:
                    raise errors.SuperdeskApiError.badRequestError("either item or item_id must be specified")
            else:
                item_id = item[ID_FIELD]

            if item is None and item_id:
                try:
                    item = await (await archive.find_async({"_id": item_id})).next()
                except StopAsyncIteration:
                    item = None
            edit = doc.pop("edit")

            # now we retrieve and load current original media
            rendition = item["renditions"]["original"]
            edit_result: AsyncTaskResult[dict] | dict = await perform_operations_in_celery.delay(rendition, edit)
            renditions = (
                await edit_result.get_result_async() if isinstance(edit_result, AsyncTaskResult) else edit_result
            )
            ids.append(item_id)
            doc["renditions"] = renditions

        return [ids]
