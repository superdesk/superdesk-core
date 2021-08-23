# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2021 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any

from superdesk.publish import register_transmitter_file_provider, TransmitterFileEntry
from superdesk.publish.transmitters.http_push import HTTPPushService


def parse_attachments(media: Dict[str, TransmitterFileEntry], item: Dict[str, Any]):
    for attachment in item.get("attachments") or []:
        media.update(
            {
                attachment["media"]: TransmitterFileEntry(
                    media=attachment["media"], mimetype=attachment["mimetype"], resource="attachments"
                )
            }
        )


def get_attachment_files_for_transmission(
    transmitter_name: str, item: Dict[str, Any]
) -> Dict[str, TransmitterFileEntry]:
    media: Dict[str, TransmitterFileEntry] = {}
    parse_attachments(media, item)

    # TODO: Review the restriction of attachments based on transmitter
    # Only transmit ``attachments`` from ``associations`` if the transmitter is HTTP Push
    # This is to keep with the current functionality
    if transmitter_name == HTTPPushService.NAME:
        for assoc in (item.get("associations") or {}).values():
            if assoc is None:
                continue
            parse_attachments(media, assoc)
            for assoc2 in (assoc.get("associations") or {}).values():
                if assoc2 is None:
                    continue
                parse_attachments(media, assoc2)

    return media


register_transmitter_file_provider(get_attachment_files_for_transmission)
