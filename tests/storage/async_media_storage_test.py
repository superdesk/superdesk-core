# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import bson
from io import BytesIO

from superdesk.tests.asyncio import AsyncTestCase
from superdesk.storage.async_storage import GridFSMediaStorageAsync


class GridFSMediaStorageAsyncTestCase(AsyncTestCase):
    app_config = {"MONGO_DBNAME": "sptests", "MODULES": ["tests.storage.modules.assests"]}

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.storage = GridFSMediaStorageAsync(self.app)

    async def test_put_and_get_file(self):
        content = BytesIO(b"Hello, GridFS!")
        filename = "testfile.txt"
        metadata = {"description": "Test file"}

        file_id = await self.storage.put(content, filename, metadata=metadata)
        self.assertIsInstance(file_id, bson.ObjectId)

        fs = await self.storage.fs()
        file = await fs.open_download_stream(file_id)

        assert file.filename == filename
        assert file.metadata["description"] == metadata["description"]

        retrieved_content = await file.read()
        assert retrieved_content == b"Hello, GridFS!"

    async def test_put_with_invalid_content_type(self):
        content = BytesIO(b"Invalid content type")
        with self.assertRaises(TypeError):
            await self.storage.put(content, content_type="invalid/type")
