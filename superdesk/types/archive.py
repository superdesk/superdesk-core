# This file is part of Superdesk
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.core.resources import ModelWithVersions
from superdesk.types.base import ItemSchema, MetadataResource


class ArchiveResourceModel(ItemSchema, MetadataResource, ModelWithVersions):
    macro: str | None = None
