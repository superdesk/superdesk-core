# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2021 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, Set
import logging

from superdesk.media.renditions import get_renditions_spec
from superdesk.publish import register_transmitter_file_provider, TransmitterFileEntry
from superdesk.publish.transmitters.ftp import FTPPublishService

logger = logging.getLogger(__name__)


def get_renditions_filter() -> Set[str]:
    renditions = set(get_renditions_spec(without_internal_renditions=True).keys())
    renditions.add("original")
    return renditions


def parse_media(media: Dict[str, TransmitterFileEntry], item: Dict[str, Any], renditions_filter: Set[str]):
    for key, rendition in (item.get("renditions") or {}).items():
        if len(renditions_filter) and key not in renditions_filter:
            continue
        elif not rendition.get("media"):
            guid = item["guid"]
            logger.warning(f"media missing on rendition {key} of item {guid}")
            continue
        rendition.pop("href", None)
        rendition.setdefault("mimetype", rendition.get("original", {}).get("mimetype", item.get("mimetype")))
        media[rendition["media"]] = rendition


def get_association_files_for_transmission(
    transmitter_name: str, item: Dict[str, Any]
) -> Dict[str, TransmitterFileEntry]:
    # TODO: Review the restriction of renditions based on transmitter
    # Attach all renditions unless the transmitter is the FTP Transmitter
    # This is to keep with the current functionality (as HTTP Push publishes all renditions)
    renditions_filter = set() if transmitter_name != FTPPublishService.NAME else get_renditions_filter()

    media: Dict[str, TransmitterFileEntry] = {}
    parse_media(media, item, renditions_filter)
    for assoc in (item.get("associations") or {}).values():
        if assoc is None:
            continue
        parse_media(media, assoc, renditions_filter)
        for assoc2 in (assoc.get("associations") or {}).values():
            if assoc2 is None:
                continue
            parse_media(media, assoc2, renditions_filter)

    return media


register_transmitter_file_provider(get_association_files_for_transmission)
