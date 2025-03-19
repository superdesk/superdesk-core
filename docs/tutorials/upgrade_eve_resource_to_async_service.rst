
Upgrading an Eve resource to use AsyncService:
==============================================

Upgrading an Eve resource to use an async service provides both sync and async access to the data it manages. This
allows to use the existing code elsewhere, while gradually upgrading everything to async.

The newly added methods to the interface are all suffixed with `_async` to:

* differentiate between the old and the new
* allow easier, smoother upgrade experience
* know which code is async or not.

Upgrading CRUD lifecycle service methods
----------------------------------------

In the service you're upgrading, if there are any methods from the table below then they must be updated to use
the ``_async`` counterpart of that method.


By upgrading all these methods to async, ensures requests coming from the REST API are using the correct
methods, along with using asyncio to access DBs etc.

.. list-table:: Eve sync vs async service methods
    :widths: 100 100
    :header-rows: 1

    * - Synchronous Access
      - Asynchronous Access
    * - on_create
      - on_create_async
    * - create
      - create_async
    * - on_created
      - on_created_async
    * - on_update
      - on_update_async
    * - update
      - update_async
    * - on_updated
      - on_updated_async
    * - on_replace
      - on_replace_async
    * - replace
      - replace_async
    * - on_replaced
      - on_replaced_async
    * - on_delete
      - on_delete_async
    * - delete
      - delete_async
    * - on_deleted
      - on_deleted_async
    * - on_fetched
      - on_fetched_async
    * - on_fetched_item
      - on_fetched_item_async
    * - system_update
      - system_update_async
    * - delete_ids_from_mongo
      - delete_ids_from_mongo_async
    * - delete_from_mongo
      - delete_from_mongo_async
    * - delete_docs
      - delete_docs_async
    * - delete_action
      - delete_action_async
    * - find
      - find_async
    * - find_one
      - find_one_async
    * - get
      - get_async
    * - get_from_mongo
      - get_from_mongo_async
    * - search
      - search_async
    * - remove_from_search
      - remove_from_search_async
    * - get_all
      - get_all_async
    * - get_all_batch
      - get_all_batch_async
    * - find_and_modify
      - find_and_modify_async
    * - post
      - post_async
    * - patch
      - patch_async
    * - put
      - put_async
    * - update_data_from_json
      - update_data_from_json_async

Example upgrading ``on_create`` method on VocabulariesService::

    class VocabulariesService(AsyncBaseService):
        async def on_create(self, docs): ...
            for doc in docs:
                self._validate_items(doc)
                ...

And change it to::

    class VocabulariesService(AsyncBaseService):
        async def on_create_async(self, docs): ...
            for doc in docs:
                await self._validate_items_async(doc)
                ...


Notice here how ``_validate_items`` was also renamed to ``_validate_items_async`` and awaited. This is because
that other method uses asyncio code, so we must upgrade that method as well to use it in this ``on_create_async`` method.

You can still use synchronous code in these new ``_async`` versions, but it's not advisable as it halts the event loop
while processing.

Upgrading other service methods
-------------------------------

Other methods on the service that are used outside the class also need to be updated to async.
If there are no I/O async calls, then leave the function as is, otherwise:

* Place an ``_async`` suffix to the method, and prefix line with ``async ``
* Rename all code that uses this method, adding ``_async`` to the end and prefixing the call with ``await``


For example, if ``add_missing_keywords`` was changed to ``add_missing_keywords_async`` like the following file
(superdesk/vocabularies/vocabularies.py)::

    class VocabulariesService(AsyncBaseService):
        def add_missing_keywords(self, keywords, language=None):
            ...
            cv = self.find_one(req=None, _id=KEYWORDS_CV)
            ...


Would be changed to::

    class VocabulariesService(AsyncBaseService):
        async def add_missing_keywords_async(self, keywords, language=None):
            ...
            cv = await self.find_one_async(req=None, _id=KEYWORDS_CV)
            ...


* If the code
* If the code is not currently async:
    * convert it to async if possible
    * otherwise leave a comment ``TODO-ASYNC[<module_name>]: Upgrade to async when upgrading this module``



How this is done depends on where the code is being changed.

Building on the example for above with ``add_missing_keywords_async`` we need to change other files that use it::

    class SomeOtherService(BaseService):
        def on_created(self, docs): ...
            service = get_resource_service("vocabularies")
            for doc in docs:
                service.add_missing_keywords(doc["keywords"], doc["language"])


Would need to be changed to::

    class SomeOtherService(BaseService):
        async def on_created(self, docs): ...
            service = get_resource_service("vocabularies")
            for doc in docs:
                await service.add_missing_keywords_async(doc["keywords"], doc["language"])
