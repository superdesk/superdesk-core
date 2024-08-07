.. _database_recording:

Database Recording
==================

Database feature was built to make it easier to prepare data for end-to-end
tests, to save and restore specific state of Superdesk during development, or to
help debugging.

It works by listening for database events when recording is started and
generates a file with changes when recording is stopped. This allows to
generate data quickly by using a browser to interact with the app while
recording is in progress.

Terminology
===========

There 2 main terms here - full dumps and records.

A full **dump** is database backup, similar to one a database management
software would generate. It is possible to have many dumps.

A **record** is a custom patch-like JSON file that gets applied to a dump to
produce a database for a specific e2e test. A dump is first required in order to
produce a record and that record only works with that dump that was used when
producing a record.

Creating a dump
===============

Run ``python manage.py storage:dump`` command. See :ref:`cli` for extra
parameters. The dump will be based on the main superdesk database used by a
local instance. In order to create a clean dump to be used for e2e tests, it’s
advised to delete the main superdesk database, initialize a clean one, add a
user and at least one desk. The same ``python manage.py storage:dump`` command
can be used to create a backup of your current development database to be
restored later.

Recording changes
=================

Recording only works with mongo 4 or greater. `Replica
mode <https://docs.mongodb.com/manual/tutorial/convert-standalone-to-replica-set/>`__
has to be enabled. To enable replica mode, add
``command: --replSet rs0`` to mongo section in ``docker-compose.yml``.
Here’s an example:

::

   mongo:
       image: mongo:4.4
       expose:
         - "27017"
       ports:
         - "27017:27017"
       command: --replSet rs0

After this, restart docker and execute the following commands in the
terminal, in the directory where your ``docker-compose.yml`` is located.

::

   > docker compose exec mongodb /bin/bash
   > mongo
   > rs.initiate()

Now run ``python manage.py storage:record`` to start recording changes.
Then open Superdesk in the browser, do the changes you need for a e2e
test and stop the recording(ctrl-c in terminal where recording was
started).

Restoring records
=================

Use :ref:`storage:restore-record <cli-storage-restore>` command.

Other commands
==============

See :ref:`storage_dumps_records`

Using recordings in e2e tests
=============================

Not implemented yet
