.. storage_async_storage:

Async Storage
=============

.. module:: superdesk.storage.async_storage.media_storage


GridFSMediaStorageAsync
-----------------------

The :class:`GridFSMediaStorageAsync` class provides an asynchronous interface for storing, retrieving, and managing files
in MongoDB's GridFS. It is designed to handle large files and provides methods for storing files with metadata,
retrieving files by ID or filename, searching for files based on criteria, checking the existence of files, and deleting files.

For example::

    async def example_usage():
        storage = GridFSMediaStorageAsync(app)
        content = BytesIO(b"Hello, GridFS!")
        filename = "example.txt"

        # Store a file
        file_id = await storage.put(content, filename, metadata={"description": "Example file"})
        print(f"Stored file ID: {file_id}")

        # Retrieve the file by ID
        media_file = await storage.get(file_id)
        if media_file:
            retrieved_content = await media_file.read()
            print(f"Retrieved content: {retrieved_content}")

        # Check if the file exists
        exists = await storage.exists(file_id)
        print(f"File exists: {exists}")

        # Delete the file
        await storage.delete(file_id)
        print("File deleted")



Module References
-----------------

.. autoclass:: superdesk.storage.async_storage.media_storage.GridFSMediaStorageAsync
    :show-inheritance:

    .. rubric:: Methods

    .. automethod:: put

        Example usage::

            async def example_put():
                storage = GridFSMediaStorageAsync(app)
                content = BytesIO(b"Hello, GridFS!")
                filename = "example.txt"
                file_id = await storage.put(content, filename, metadata={"description": "Example file"})
                print(f"Stored file ID: {file_id}")

    .. automethod:: get

        Example usage::

            async def example_get():
                storage = GridFSMediaStorageAsync(app)
                file_id = ObjectId("60c72b2f9af1c7268b8b4567")
                media_file = await storage.get(file_id)
                if media_file:
                    content = await media_file.read()
                    print(f"Retrieved content: {content}")

    .. automethod:: find

        Example usage::

            async def example_find():
                storage = GridFSMediaStorageAsync(app)
                files = await storage.find(folder="example_folder")
                for file in files:
                    print(f"Found file: {file['filename']}")

    .. automethod:: exists

        Example usage::

            async def example_exists():
                storage = GridFSMediaStorageAsync(app)
                file_id = ObjectId("60c72b2f9af1c7268b8b4567")
                exists = await storage.exists(file_id)
                print(f"File exists: {exists}")

    .. automethod:: delete

        Example usage::

            async def example_delete():
                storage = GridFSMediaStorageAsync(app)
                file_id = ObjectId("60c72b2f9af1c7268b8b4567")
                await storage.delete(file_id)
                print("File deleted")

    .. automethod:: get_by_filename

        Example usage::

            async def example_get_by_filename():
                storage = GridFSMediaStorageAsync(app)
                filename = "example.txt"
                media_file = await storage.get_by_filename(filename)
                if media_file:
                    content = await media_file.read()
                    print(f"Retrieved content by filename: {content}")

    .. automethod:: fs

