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

.. autoclass:: superdesk.commands.clean_images.CleanImages()

``app:deleteArchivedDocument``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.commands.delete_archived_document.DeleteArchivedDocumentCommand()

``app:index_from_mongo``
^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.commands.index_from_mongo.IndexFromMongo()

``app:initialize_data``
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: apps.prepopulate.app_initialize.AppInitializeWithDataCommand()

``app:flush_elastic_index``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.commands.flush_elastic_index.FlushElasticIndex()

``app:prepopulate``
^^^^^^^^^^^^^^^^^^^

.. autoclass:: apps.prepopulate.app_prepopulate.AppPrepopulateCommand()

``app:populate``
^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: apps.prepopulate.app_populate.AppPopulateCommand()

``app:rebuild_elastic_index``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.commands.rebuild_elastic_index.RebuildElasticIndex()

``app:run_macro``
^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.commands.run_macro.RunMacro()

``app:scaffold_data``
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: apps.prepopulate.app_scaffold_data.AppScaffoldDataCommand()

``app:updateArchivedDocument``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.commands.update_archived_document.UpdateArchivedDocumentCommand()

``archive:remove_expired``
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: apps.archive.commands.RemoveExpiredContent()

``audit:purge``
^^^^^^^^^^^^^^^

.. autoclass:: superdesk.audit.commands.PurgeAudit()

``content_api:remove_expired``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: content_api.commands.remove_expired_items.RemoveExpiredItems()

``data:generate_update``
^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.commands.data_updates.GenerateUpdate()

``data:upgrade``
^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.commands.data_updates.Upgrade()

``data:downgrade``
^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.commands.data_updates.Downgrade()

``ingest:clean_expired``
^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.io.commands.remove_expired_content.RemoveExpiredContent()

``ingest:provider``
^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.io.commands.add_provider.AddProvider()

``ingest:update``
^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.io.commands.update_ingest.UpdateIngest()

``legal_archive:import``
^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: apps.legal_archive.commands.ImportLegalArchiveCommand()

``legal_publish_queue:import``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: apps.legal_archive.commands.ImportLegalPublishQueueCommand()

``publish:enqueue``
^^^^^^^^^^^^^^^^^^^

.. autoclass:: apps.publish.enqueue.EnqueueContent()

``publish:transmit``
^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.publish.publish_content.PublishContent()

``session:gc``
^^^^^^^^^^^^^^

.. autoclass:: apps.auth.session_purge.RemoveExpiredSessions()

``schema:migrate``
^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.commands.schema.SchemaMigrateCommand()

``storage:remove_exported``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.commands.remove_exported_files.RemoveExportedFiles()

``users:create``
^^^^^^^^^^^^^^^^

.. autoclass:: apps.auth.db.commands.CreateUserCommand()

``users:import``
^^^^^^^^^^^^^^^^

.. autoclass:: apps.auth.db.commands.ImportUsersCommand()

``users:copyfromad``
^^^^^^^^^^^^^^^^^^^^

.. autoclass:: apps.ldap.commands.ImportUserProfileFromADCommand()

``users:get_auth_token``
^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: apps.auth.db.commands.GetAuthTokenCommand()

``users:hash_passwords``
^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: apps.auth.db.commands.HashUserPasswordsCommand()

``vocabularies:generate``
^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.commands.generate_vocabularies.GenerateVocabularies()


``vocabularies:update_archive``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.vocabularies.commands.UpdateVocabulariesInItemsCommand()

``xml:import``
^^^^^^^^^^^^^^

.. autoclass:: superdesk.io.importers.ImportCommand()

``auth_server:register_client``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.auth_server.clients.RegisterClient()

``auth_server:update_client``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.auth_server.clients.UpdateClient()

``auth_server:unregister_client``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.auth_server.clients.UnregisterClient()

``auth_server:list_clients``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.auth_server.clients.ListClients()
