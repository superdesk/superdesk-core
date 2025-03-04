from quart import abort

import pymongo
from motor.motor_asyncio import AsyncIOMotorCollection
from eve.io.base import ConnectionException
from eve.utils import config, debug_error_message, validate_filters

from eve.io.mongo.mongo import Mongo
from .flask_mongo_async import FlaskMongoAsync


class MongoAsync(Mongo):
    def pymongo(self, resource=None, prefix=None) -> FlaskMongoAsync:
        px = prefix if prefix else self.current_mongo_prefix(resource=resource)

        if px not in self.driver:
            # instantiate and add to cache
            self.driver[px] = FlaskMongoAsync(self.app, px)

        # important, we don't want to preserve state between requests
        self.mongo_prefix = None

        try:
            return self.driver[px]
        except Exception as e:
            raise ConnectionException(e)

    def get_collection_with_write_concern(self, datasource, resource) -> AsyncIOMotorCollection:
        wc = pymongo.WriteConcern(config.DOMAIN[resource]["mongo_write_concern"]["w"])
        return self.pymongo(resource).db[datasource].with_options(write_concern=wc)

    async def find(self, resource, req, sub_resource_lookup, perform_count=True):
        args = {}

        if req and req.max_results:
            args["limit"] = req.max_results

        if req and req.page > 1:
            args["skip"] = (req.page - 1) * req.max_results

        client_sort = self._convert_sort_request_to_dict(req)
        spec = self._convert_where_request_to_dict(resource, req)

        bad_filter = validate_filters(spec, resource)
        if bad_filter:
            abort(400, bad_filter)

        if sub_resource_lookup:
            spec = self.combine_queries(spec, sub_resource_lookup)

        if (
            config.DOMAIN[resource]["soft_delete"]
            and not (req and req.show_deleted)
            and not self.query_contains_field(spec, config.DELETED)
        ):
            # Soft delete filtering applied after validate_filters call as
            # querying against the DELETED field must always be allowed when
            # soft_delete is enabled
            spec = self.combine_queries(spec, {config.DELETED: {"$ne": True}})

        spec = self._mongotize(spec, resource)

        client_projection = self._client_projection(req)

        datasource, spec, projection, sort = self._datasource_ex(resource, spec, client_projection, client_sort)

        if req and req.if_modified_since:
            spec[config.LAST_UPDATED] = {"$gt": req.if_modified_since}

        if len(spec) > 0:
            args["filter"] = spec

        if sort is not None:
            args["sort"] = sort

        if projection:
            args["projection"] = projection

        target = self.pymongo(resource).db[datasource]
        try:
            result = target.find(**args)
        except TypeError as e:
            # pymongo raises ValueError when invalid query paramenters are
            # included. We do our best to catch them beforehand but, especially
            # with key/value sort syntax, invalid ones might still slip in.
            self.app.logger.exception(e)
            abort(400, description=debug_error_message(str(e)))

        count = await target.count_documents(spec) if perform_count else None

        return result, count

    async def find_one(
        self, resource, req, check_auth_value=True, force_auth_field_projection=False, mongo_options=None, **lookup
    ):
        self._mongotize(lookup, resource)

        client_projection = self._client_projection(req)

        datasource, filter_, projection, _ = self._datasource_ex(
            resource,
            lookup,
            client_projection,
            check_auth_value=check_auth_value,
            force_auth_field_projection=force_auth_field_projection,
        )

        if (
            (config.DOMAIN[resource]["soft_delete"])
            and (not req or not req.show_deleted)
            and (not self.query_contains_field(lookup, config.DELETED))
        ):
            filter_ = self.combine_queries(filter_, {config.DELETED: {"$ne": True}})
        # Here, we feed pymongo with `None` if projection is empty.
        target = self.pymongo(resource).db[datasource]
        if mongo_options:
            return await target.with_options(**mongo_options).find_one(filter_, projection or None)
        return await target.find_one(filter_, projection or None)

    async def find_one_raw(self, resource, **lookup):
        id_field = config.DOMAIN[resource]["id_field"]
        _id = lookup.get(id_field)
        datasource, filter_, _, _ = self._datasource_ex(resource, {id_field: _id}, None)

        lookup = self._mongotize(lookup, resource)

        return await self.pymongo(resource).db[datasource].find_one(lookup)

    async def find_list_of_ids(self, resource, ids, client_projection=None):
        id_field = config.DOMAIN[resource]["id_field"]
        query = {"$or": [{id_field: id_} for id_ in ids]}

        datasource, spec, projection, _ = self._datasource_ex(
            resource, query=query, client_projection=client_projection
        )
        # projection of {} return all fields in MongoDB, but
        # pymongo will only return `_id`. It's a design flaw upstream.
        # Here, we feed pymongo with `None` if projection is empty.
        documents = self.pymongo(resource).db[datasource].find(filter=spec, projection=(projection or None))
        return documents

    def aggregate(self, resource, pipeline, options):
        datasource, _, _, _ = self.datasource(resource)
        challenge = self._mongotize({"key": pipeline}, resource)["key"]

        return self.pymongo(resource).db[datasource].aggregate(challenge, **options)

    async def insert(self, resource, doc_or_docs):
        datasource, _, _, _ = self._datasource_ex(resource)

        coll = self.get_collection_with_write_concern(datasource, resource)

        if isinstance(doc_or_docs, dict):
            doc_or_docs = [doc_or_docs]

        try:
            return (await coll.insert_many(doc_or_docs, ordered=True)).inserted_ids
        except pymongo.errors.BulkWriteError as e:
            self.app.logger.exception(e)

            # since this is an ordered bulk operation, all remaining inserts
            # are aborted. Be aware that if BULK_ENABLED is True and more than
            # one document is included with the payload, some documents might
            # have been successfully inserted, even if the operation was
            # aborted.

            # report a duplicate key error since this can probably be
            # handled by the client.
            for error in e.details["writeErrors"]:
                # amazingly enough, pymongo does not appear to be exposing
                # error codes as constants.
                if error["code"] == 11000:
                    abort(
                        409,
                        description=debug_error_message(
                            "Duplicate key error at index: %s, message: %s" % (error["index"], error["errmsg"])
                        ),
                    )

            abort(
                500,
                description=debug_error_message("pymongo.errors.BulkWriteError: %s" % e),
            )

    async def _change_request(self, resource, id_, changes, original, replace=False):
        id_field = config.DOMAIN[resource]["id_field"]
        query = {id_field: id_}
        if config.ETAG in original:
            query[config.ETAG] = original[config.ETAG]

        datasource, filter_, _, _ = self._datasource_ex(resource, query)

        coll = self.get_collection_with_write_concern(datasource, resource)
        try:
            result = await (coll.replace_one(filter_, changes) if replace else coll.update_one(filter_, changes))
            if config.ETAG in original and result and result.acknowledged and result.modified_count == 0:
                raise self.OriginalChangedError()
        except pymongo.errors.DuplicateKeyError as e:
            abort(
                400,
                description=debug_error_message("pymongo.errors.DuplicateKeyError: %s" % e),
            )
        except (pymongo.errors.WriteError, pymongo.errors.OperationFailure) as e:
            # server error codes and messages changed between 2.4 and 2.6/3.0.
            server_version = self.driver.db.client.server_info()["version"][:3]
            if (server_version == "2.4" and e.code in (13596, 10148)) or e.code in (
                66,
                16837,
            ):
                # attempt to update an immutable field. this usually
                # happens when a PATCH or PUT includes a mismatching ID_FIELD.
                self.app.logger.warning(e)
                description = (
                    debug_error_message("pymongo.errors.OperationFailure: %s" % e)
                    or "Attempt to update an immutable field. Usually happens "
                    "when PATCH or PUT include a '%s' field, "
                    "which is immutable (PUT can include it as long as "
                    "it is unchanged)." % id_field
                )

                abort(400, description=description)
            else:
                # see comment in :func:`insert()`.
                self.app.logger.exception(e)
                abort(
                    500,
                    description=debug_error_message("pymongo.errors.OperationFailure: %s" % e),
                )

    async def update(self, resource, id_, updates, original):
        return await self._change_request(resource, id_, {"$set": updates}, original)

    async def replace(self, resource, id_, document, original):
        return await self._change_request(resource, id_, document, original, replace=True)

    async def remove(self, resource, lookup):
        lookup = self._mongotize(lookup, resource)
        datasource, filter_, _, _ = self._datasource_ex(resource, lookup)

        coll = self.get_collection_with_write_concern(datasource, resource)
        try:
            await coll.delete_many(filter_)
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            self.app.logger.exception(e)
            abort(
                500,
                description=debug_error_message("pymongo.errors.OperationFailure: %s" % e),
            )

    async def is_empty(self, resource):
        datasource, filter_, _, _ = self.datasource(resource)
        coll = self.pymongo(resource).db[datasource]
        try:
            if not filter_:
                # faster, but we can only afford it if there's now predefined
                # filter on the datasource.
                return (await coll.count_documents({})) == 0
            # fallback on find() since we have a filter to apply.
            try:
                # need to check if the whole resultset is missing, no
                # matter the IMS header.
                del filter_[config.LAST_UPDATED]
            except Exception:
                pass
            return (await coll.count_documents(filter_)) == 0
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            self.app.logger.exception(e)
            abort(
                500,
                description=debug_error_message("pymongo.errors.OperationFailure: %s" % e),
            )
