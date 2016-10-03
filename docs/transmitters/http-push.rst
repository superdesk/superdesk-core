HTTP Push
=========

The HTTP push service publishes items to the resource service via ``POST`` request. For media items it first publishes the media files to the assets service.

For text items the publish sequence is like this:

* ``POST`` to resource service the text item

For media items the publish sequence is like this:

* Publish media files: for each file from renditions perform the following steps:

    * Verify if the rendition media file exists in the assets service (``GET assets/{media_id}``)
    * If not, upload the rendition media file to the assets service via ``POST`` request

* Publish the item

For package items with embedded items config on there is only one publish request to the resource service.

For package items without embedded items the publish sequence is like this:

* Publish package items
* Publish the package item


Publishing of an asset
----------------------

The ``POST`` request to the assets ``URL`` has the ``multipart/data-form`` content type and should contain the following fields:

``media_id``
    URI string identifing the rendition.

``media``
    ``base64`` encoded file content. See `Eve documentation <http://python-eve.org/features.html#file-storage>`_.

``mime_type``
    mime type, eg. ``image/jpeg``.

``filemeta``
    metadata extracted from binary. Differs based on binary type, eg. could be exif for pictures.

The response status code is checked - on success it should be ``201 Created``.
