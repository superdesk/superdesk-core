# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
from io import BytesIO
from bson import ObjectId
from datetime import datetime, timezone, timedelta

from superdesk.tests.asyncio import AsyncTestCase
from superdesk.storage.async_storage import GridFSMediaStorageAsync


class GridFSMediaStorageAsyncTestCase(AsyncTestCase):
    app_config = {"MONGO_DBNAME": "sptests", "MODULES": ["tests.storage.modules.assests"]}

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.storage = GridFSMediaStorageAsync()

    async def test_put_and_get_file(self):
        content = BytesIO(b"Hello, GridFS!")
        filename = "testfile.txt"
        metadata = {"description": "Test file"}

        file_id = await self.storage.put(content, filename, metadata=metadata)
        self.assertIsInstance(file_id, ObjectId)

        fs = await self.storage.fs()
        file = await fs.open_download_stream(file_id)

        self.assertEqual(file.filename, filename)
        self.assertEqual(file.metadata["description"], metadata["description"])

        retrieved_content = await file.read()
        self.assertEqual(retrieved_content, b"Hello, GridFS!")

    async def test_put_with_invalid_content_type(self):
        content = BytesIO(b"Invalid content type")
        with self.assertRaises(TypeError):
            await self.storage.put(content, content_type="invalid/type")

    async def test_put_and_get_file_with_existing_id(self):
        content = BytesIO(b"File with custom ID")
        filename = "file_with_id.txt"
        file_id = ObjectId()

        await self.storage.put(content, filename, _id=file_id)
        fs = await self.storage.fs()
        file = await fs.open_download_stream(file_id)
        retrieved_content = await file.read()

        self.assertEqual(retrieved_content, b"File with custom ID")

    async def test_get_file(self):
        content = BytesIO(b"Hello, GridFS!")
        filename = "testfile.txt"
        metadata = {"description": "Test file"}

        file_id = await self.storage.put(content, filename, metadata=metadata)
        media_file = await self.storage.get(file_id)

        self.assertEqual(media_file.filename, filename)
        self.assertEqual(media_file.metadata["description"], metadata["description"])

        retrieved_content = await media_file.read()
        self.assertEqual(retrieved_content, b"Hello, GridFS!")

    async def test_get_nonexistent_file(self):
        file_id = ObjectId()
        media_file = await self.storage.get(file_id)
        self.assertIsNone(media_file)

    async def test_find_by_folder(self):
        content = BytesIO(b"Hello, GridFS!")
        filename = "folder1/testfile1.txt"
        metadata = {"description": "Test file in folder1"}
        await self.storage.put(content, filename, metadata=metadata)

        filename = "folder1/testfile2.txt"
        metadata = {"description": "Another test file in folder1"}
        await self.storage.put(content, filename, metadata=metadata)

        filename = "folder2/testfile3.txt"
        metadata = {"description": "Test file in folder2"}
        await self.storage.put(content, filename, metadata=metadata)

        # find files in folder1
        files = await self.storage.find(folder="folder1")
        self.assertEqual(len(files), 2)
        self.assertTrue(all("folder1/" in file["filename"] for file in files))

    async def test_find_by_upload_date(self):
        # store files with different upload dates
        now = datetime.now(timezone.utc)
        past_date = now - timedelta(days=1)
        future_date = now + timedelta(days=1)

        content = BytesIO(b"File content")
        filename = "testfile_past.txt"
        metadata = {"description": "Test file in the past"}
        await self.storage.put(content, filename, metadata=metadata)

        filename = "testfile_future.txt"
        metadata = {"description": "Test file in the future"}
        await self.storage.put(content, filename, metadata=metadata)

        # find files with upload date less than now
        files = await self.storage.find(upload_date={"$lt": future_date})
        self.assertTrue(any(file["filename"] == "testfile_past.txt" for file in files))

        # find files with upload date greater than now
        files = await self.storage.find(upload_date={"$gt": past_date})
        self.assertTrue(any(file["filename"] == "testfile_future.txt" for file in files))

    async def test_exists_by_id(self):
        content = BytesIO(b"Hello, GridFS!")
        filename = "testfile.txt"
        metadata = {"description": "Test file"}

        file_id = await self.storage.put(content, filename, metadata=metadata)
        self.assertIsInstance(file_id, ObjectId)

        exists = await self.storage.exists(file_id)
        self.assertTrue(exists)

        non_existent_id = ObjectId()
        exists = await self.storage.exists(non_existent_id)
        self.assertFalse(exists)

    async def test_exists_by_query(self):
        content = BytesIO(b"Hello, GridFS!")
        filename = "testfile_query.txt"
        metadata = {"description": "Test file for query"}

        file_id = await self.storage.put(content, filename, metadata=metadata)
        self.assertIsInstance(file_id, ObjectId)

        query = {"filename": filename}
        exists = await self.storage.exists(query)
        self.assertTrue(exists)

        non_existent_query = {"filename": "non_existent_file.txt"}
        exists = await self.storage.exists(non_existent_query)
        self.assertFalse(exists)

    async def test_delete_existing_file(self):
        content = BytesIO(b"Hello, GridFS!")
        filename = "testfile_to_delete.txt"
        metadata = {"description": "File to be deleted"}

        file_id = await self.storage.put(content, filename, metadata=metadata)
        self.assertIsInstance(file_id, ObjectId)

        exists = await self.storage.exists(file_id)
        self.assertTrue(exists)

        await self.storage.delete(file_id)

        exists = await self.storage.exists(file_id)
        self.assertFalse(exists)

    async def test_delete_nonexistent_file(self):
        non_existent_id = ObjectId()

        await self.storage.delete(non_existent_id)

        exists = await self.storage.exists(non_existent_id)
        self.assertFalse(exists)

    async def test_get_by_filename(self):
        content = BytesIO(b"Hello, GridFS!")
        filename = "testfile_by_filename.txt"
        metadata = {"description": "Test file for get_by_filename"}

        custom_id, _ = os.path.splitext(filename)
        await self.storage.put(content, filename, metadata=metadata, _id=custom_id)
        media_file = await self.storage.get_by_filename(filename)

        self.assertIsNotNone(media_file)
        self.assertEqual(media_file.filename, filename)
        self.assertEqual(media_file.metadata["description"], metadata["description"])

        retrieved_content = await media_file.read()
        self.assertEqual(retrieved_content, b"Hello, GridFS!")

    async def test_get_by_nonexistent_filename(self):
        non_existent_filename = "non_existent_file.txt"
        media_file = await self.storage.get_by_filename(non_existent_filename)
        self.assertIsNone(media_file)
