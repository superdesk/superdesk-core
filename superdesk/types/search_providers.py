# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.core.resources.model import dataclass


class SearchProvider:
    """Base class for Search Providers.

    You can use ``self.provider`` to get config data.
    """

    #: Provider Type Label
    label: str = "unknown"

    def __init__(self, provider: dict):
        """Create search provider instance.

        :param provider: provider data dict
        """
        self.provider = provider

    async def find(self, query: dict, params: dict | None = None):
        """Find items using query.

        This must return cursor like object.

        :param query: query dict
        """
        raise NotImplementedError

    async def fetch(self, guid: str):
        """Get single item.

        Get an item before archiving it. Should contain all metadata.

        :param guid: item guid
        """
        raise NotImplementedError

    async def fetch_file(self, href: str):
        """Fetch binary using given href.

        Href is from renditions dict.

        :param href: binary href
        """
        raise NotImplementedError


@dataclass
class SearchProviderData:
    name: str
    endpoint: str | None = None
    provider_class: type[SearchProvider] | None = None
    label: str | None = None
