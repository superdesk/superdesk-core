Content Expiry
==============

Production content
------------------

By default content in production will expire after **30 days** of inactivity.
This value can be modified via ``CONTENT_EXPIRY_MINUTES`` config option in settings.
If an expiry-date calculation overflows, it logs a warning and uses **99,999 days**
from the calculation's base timestamp instead of disabling expiry. This applies
to the shared expiry calculation for production, ingest, spiked and published
content, as well as ``archive:set_expiry``.

Default value can be overridden via desk configuration. There you can specify
different expiry for both desk and stage. When an item is updated, it will modify its
expiry using value from:

1. current stage if set
2. current desk if set
3. default value from config

Thus there is always some expiry value in place, even if not set on a desk or stage.
Content which expires in production will be removed without any traces left.

To reset expiry on existing active unpublished items on a desk, use::

    $ python manage.py archive:set_expiry --desk Sports --days 999
    $ python manage.py archive:set_expiry --desk Sports --days 999 --from-updated
    $ python manage.py archive:set_expiry --desk "Sports News"

``--desk`` is the exact desk name. ``--days`` must be a positive integer and
overrides configured expiry. Without it, stage, desk and global settings are
used in the order above. By default, expiry is calculated from the command's
start time. Add ``--from-updated`` to calculate it from each item's last-updated
timestamp instead, with either ``--days`` or configured expiry. This can make
older items immediately eligible for expiry removal. A disabled configured
expiry clears the item's explicit expiry.
The desk configuration is reused and each stage is fetched at most once per
command run, across all batches.

The command handles draft, ingested, routed, fetched, submitted and in-progress
items only. It leaves spiked, scheduled and published content (including
corrections) untouched. Updates are applied to both MongoDB and Elasticsearch
without changing the current version, version history or etag. Successful writes
refresh the last-updated timestamp. With ``--from-updated``, expiry is calculated
from the timestamp fetched before this refresh. Subsequent editorial updates
will recalculate expiry normally.
Items with invalid timestamps or expiry configuration are logged and skipped;
the command reports the skipped count and continues with other items. Storage
failures still stop the command.
Writes use the MongoDB backend's atomic item ID and fetched etag check.
This uses ``system_update(..., check_etag=True)``, which raises
``UpdateConflictError`` on a mismatch or removal before indexing or notifying.
This plain exception carries ``resource`` and ``item_id`` attributes and chains
the original backend exception as its cause.
The option defaults to false, preserving existing unchecked system updates.
Items whose etag changed, or which were removed since the batch
read, are logged and skipped without indexing or counting them as updated.
Desk/state eligibility is checked at batch selection; concurrent changes must
update the etag to be detected. Timestamp-only changes are not detected.
The backend also treats no-op writes as conflicts. Only expiry and last-updated are
written; other stored metadata is left untouched.

Published content
-----------------

Published content will be in ``published`` collection for ``PUBLISHED_CONTENT_EXPIRY_MINUTES``,
after that it will be still available in ``archived`` collection.

Ingest content expiry
---------------------

It uses ``INGEST_EXPIRY_MINUTES`` config, which is set to **2 days** by default.
