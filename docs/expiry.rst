Content Expiry
==============

Production content
------------------

By default content in production will expire after **30 days** of inactivity.
This value can be modified via ``CONTENT_EXPIRY_MINUTES`` config option in settings.

Default value can be overridden via desk configuration. There you can specify
different expiry for both desk and stage. When an item is updated, it will modify its
expiry using value from:

1. current stage if set
2. current desk if set
3. default value from config

Thus there is always some expiry value in place, even if not set on a desk or stage.
Content which expires in production will be removed without any traces left.

Published content
-----------------

Published content will be in ``published`` collection for ``CONTENT_EXPIRY_MINUTES``,
after that it will be still available in ``archived`` collection.

Ingest content expiry
---------------------

It uses ``INGEST_EXPIRY_MINUTES`` config, which is set to **2 days** by default.
