# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json

from quart.utils import run_sync

from superdesk.core import get_app_config
from superdesk.publish import register_transmitter
from superdesk.publish.publish_service import PublishService
from superdesk.errors import PublishODBCError

try:
    import pyodbc

    pyodbc_available = True
except ImportError:
    pyodbc_available = False

errors = [PublishODBCError.odbcError().get_error_description()]


class ODBCPublishService(PublishService):
    """Superdesk ODBC transmitter.

    Calls a stored procedure with item data.

    :param string connection_string:
    :param string stored_procedure:
    """

    NAME = "ODBC"

    async def _transmit(self, queue_item, subscriber):
        """
        Transmit the given formatted item to the configured ODBC output.

        Configuration must have connection string and the name of a stored procedure.
        """

        if not get_app_config("ODBC_PUBLISH") or not pyodbc_available:
            raise await PublishODBCError().send_notifications()

        config = queue_item.get("destination", {}).get("config", {})

        try:
            # Note: No suitable library found for ODBC, so pushing this to a separate thread
            # so we aren't holding up the current event loop
            return await run_sync(self._store_data)(
                config["connection_string"], json.loads(queue_item["formatted_item"]), config["stored_procedure"]
            )
        except Exception as ex:
            raise await PublishODBCError.odbcError(ex, config).send_notifications()

    def _store_data(self, connection_string, data, stored_procedure):
        with pyodbc.connect(connection_string) as conn:
            ret = self._CallStoredProc(conn, procName=stored_procedure, paramDict=data)
            conn.commit()
        return ret

    def _CallStoredProc(self, conn, procName, paramDict):
        params = ""
        for p in paramDict:
            if paramDict[p]:
                params += "@{}=N'{}', ".format(p, paramDict[p])
        params = params[:-2]
        sql = """SET NOCOUNT ON;
             DECLARE @ret int
             EXEC @ret = %s %s
             SELECT @ret""" % (
            procName,
            params,
        )
        resp = conn.execute(sql).fetchone()
        if resp is not None:
            return resp[0]
        else:
            return 1


if pyodbc_available:
    register_transmitter("ODBC", ODBCPublishService(), errors)
