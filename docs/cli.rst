.. _cli:

Superdesk CLI
=============

In ``superdesk/server`` folder you can find ``manage.py`` file which you can use
to run commands from CLI::

    $ python manage.py

With no other argument it will output list of all available commands.
To run specific command you use its name and any params needed::

    $ python manage.py users:create -u admin -p admin

Creating new command
--------------------

You can create new commands extending :class:`superdesk.Command` and registering it using
:meth:`superdesk.command` call::

    import superdesk

    class HelloWorldCommand(superdesk.Command):

        option_list = [
            superdesk.Option('--name', '-n', required=True),
        ]

        def run(self, name):
            print('hello {}'.format(name))


    superdesk.command('hello:word', MyCommand())

We use `Flask-Script <https://flask-script.readthedocs.io/>`_ under the hood so you can get more info there.

Superdesk commands
------------------

``app:clean_images``
^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.clean_images.cli_clean_images()

``app:deleteArchivedDocument``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.delete_archived_document.cli_delete_archived_document()

``app:index_from_mongo``
^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.index_from_mongo.cli_index_from_mongo()

``app:initialize_data``
^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: apps.prepopulate.app_initialize.app_initialize_data_command()

``app:flush_elastic_index``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.flush_elastic_index.flush_elastic_index_command()

``app:prepopulate``
^^^^^^^^^^^^^^^^^^^

.. autofunction:: apps.prepopulate.app_prepopulate.cli_app_prepopulate()

``app:populate``
^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: apps.prepopulate.app_populate.cli_app_populate()

``app:rebuild_elastic_index``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.rebuild_elastic_index.cli_rebuild_elastic_index()

``app:run_macro``
^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.run_macro.run_macro()

``app:scaffold_data``
^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: apps.prepopulate.app_scaffold_data.scaffold_data_command()

``app:updateArchivedDocument``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.update_archived_document.cli_update_archived_document()

``archive:remove_expired``
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: apps.archive.commands.cli_archive_remove_expired()

``audit:purge``
^^^^^^^^^^^^^^^

.. autofunction:: superdesk.audit.commands.cli_audit_purge()

``content_api:remove_expired``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: content_api.commands.remove_expired_items.cli_content_api_remove_expired()

``data:generate_update``
^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.data_updates.cli_data_generate_update()

``data:upgrade``
^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.data_updates.upgrade_command()

``data:downgrade``
^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.data_updates.downgrade_command()

``ingest:clean_expired``
^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.io.commands.remove_expired_content.cli_ingest_clean_expired()

``ingest:provider``
^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.io.commands.add_provider.cli_add_provider()

``ingest:update``
^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.io.commands.update_ingest.cli_update_ingest()

``legal_archive:import``
^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: apps.legal_archive.commands.cli_legal_archive_import()

``legal_publish_queue:import``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: apps.legal_archive.commands.cli_legal_publish_queue_import()

``publish:enqueue``
^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.publish_async.commands.publish_scheduled_items()

``publish:transmit``
^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.publish_async.commands.publish_pending_items()

``session:gc``
^^^^^^^^^^^^^^

.. autofunction:: apps.auth.session_purge.cli_session_gc()

``schema:migrate``
^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.schema.schema_migrate_command()

.. _storage_dumps_records:

Storage Dumps and Records
=========================

.. note::

    You can check :ref:`database_recording` for details on how to use following
    ``storage:…`` commands.

``storage:dump``
^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.data_manipulation.cli_data_storage_dump

.. _cli-storage-restore:

``storage:restore``
^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.data_manipulation.cli_data_storage_restore

``storage:record``
^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.data_manipulation.cli_data_storage_record

``storage:restore-record``
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.data_manipulation.cli_data_storage_restore_record

``storage:list``
^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.data_manipulation.cli_data_storage_list

``storage:upgrade-dumps``
^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.data_manipulation.cli_data_storage_upgrade_dumps

``storage:remove_exported``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.remove_exported_files.cli_storage_remove_exported()

``users:create``
^^^^^^^^^^^^^^^^

.. autofunction:: apps.auth.db.commands.create_user_command()

``users:import``
^^^^^^^^^^^^^^^^

.. autofunction:: apps.auth.db.commands.cli_users_import()

``users:copyfromad``
^^^^^^^^^^^^^^^^^^^^

.. autofunction:: apps.ldap.commands.cli_users_copyfromad()

``users:get_auth_token``
^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: apps.auth.db.commands.cli_users_get_auth_token()

``users:hash_passwords``
^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: apps.auth.db.commands.cli_users_hash_passwords()

``vocabularies:generate``
^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.commands.generate_vocabularies.cli_generate_vocabularies()


``vocabularies:update_archive``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.vocabularies.commands.update_vocabularies_in_items_command()

``xml:import``
^^^^^^^^^^^^^^

.. autofunction:: superdesk.io.importers.cli_xml_import()

``auth_server:register_client``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.auth_server.clients.cli_auth_server_register_client()

``auth_server:update_client``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.auth_server.clients.cli_auth_server_update_client()

``auth_server:unregister_client``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.auth_server.clients.cli_auth_server_unregister_client()

``auth_server:list_clients``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.auth_server.clients.cli_auth_server_list_clients()

``media:fix_links``
^^^^^^^^^^^^^^^^^^^

.. autofunction:: superdesk.storage.fix_links.cli_media_fix_links()
