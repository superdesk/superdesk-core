API
===

Here is a quick overview of Superdesk API


Staged media uploads
--------------------

Upload a binary as multipart ``media`` to ``POST /upload_staging``. The response includes
processing ``status`` and ``metadata_status``. The request only stores the binary and
queues processing: metadata extraction and rendition generation run in a Celery worker.
Workers stream stored files to temporary disk files for metadata parsing rather than
loading the whole binary into Python memory.

Listen for ``upload_staging:updated`` websocket events (``staged_id`` and ``user`` identify
the affected upload) and refresh it with ``GET /upload_staging/<id>``. Also refresh once
after the POST and on websocket reconnection to recover missed notifications. The client
does not repeatedly poll. Events contain no metadata; GET remains owner-restricted.
Status refreshes bypass the client's short-lived duplicate-GET cache, and each snapshot
is applied before starting the next refresh.

``metadata_status`` is ``pending``, ``ready``, or ``failed``. Once extraction completes,
``meta`` contains mapped article fields and ``raw_metadata`` contains embedded IPTC/XMP.
Metadata failure includes ``metadata_error`` and permits manual entry, without blocking
rendition generation. The editor applies extracted defaults only once, preserving edits.
Each file keeps its own embedded metadata even when extraction completes at different
times. Only explicit bulk edits are carried forward to files arriving in the editor later.
Before metadata is available, the client shows a separate file preview with upload progress
followed by a reading-metadata indicator. Pending files can be removed without opening the editor.

Image renditions start immediately after metadata extraction, reusing the same temporary
file so the worker downloads the original only once. Metadata is persisted and its
notification sent before rendition generation begins. Video processing is deferred:
``status`` becomes ``awaiting_confirmation`` until the user confirms via
``PATCH /upload_staging/<id>`` with ``{"confirmed": true}`` (and ``If-Match``).
The worker then performs video server upload/timeline generation if configured.
Other processing states are ``pending``, ``processing``, ``ready``, and ``failed``.
A rendition failure includes an ``error`` message; discard the file and upload it again.
Processing updates are persisted in MongoDB: this flow does not store or retrieve Celery task results.
Each worker state change refreshes ``_updated`` and ``_etag`` atomically with the data,
so conditional GETs after a notification return the new metadata or renditions.

Once ready, ``POST /archive`` with ``staged_id`` and the edited article fields. The server
reuses the stored binary and renditions without waiting for a worker. A premature commit
returns HTTP 409. Staged files are owner-restricted and can be committed only once.
Before archive creation, staging enters ``committing`` and reserves an archive ID.
If validation or insertion fails, retry the same ``staged_id``: it reuses that ID,
preventing concurrent retries from creating duplicate items. Staging is finalized only
after archive persistence, never during the pre-create hook. Committing uploads cannot
be discarded while creation may still be in flight. Expiry cleanup reconciles unfinished
commits with the archive, preserving media belonging to persisted items.
The client allows Upload confirmation while renditions are still running, waits for the
ready notification, and commits automatically without requiring another click.

Discard with ``DELETE /upload_staging/<id>`` using the response's ``_etag`` in ``If-Match``.
This removes the binary and generated renditions. Workers also clean up their output if
discard occurs during processing.
Worker updates may invalidate ``If-Match`` between a GET and confirmation or discard.
The client handles HTTP 412 by fetching a fresh, uncached snapshot and retrying, with at
most three mutation attempts. A failed Remove keeps the file visible for another attempt.

``UPLOAD_STAGING_TTL`` defaults to six hours. Celery beat schedules
``apps.archive.upload_staging.expire_staged_uploads`` every five minutes to remove expired
uploads and their media. A worker and beat must be running; no Celery results backend is
needed for staging. Legacy, non-staged archive uploads retain their existing processing flow.

When updating a development database that used the earlier staging TTL index, drop
``upload_staging.expires_1`` and reinitialize indexes. The new index on ``expires`` is
non-TTL: direct MongoDB expiry would bypass media cleanup.


Media Editor
------------
Media Editor do requested transformations on a media (images only for now).

client can use "media_editor" endpoint to transform an image.
A `POST` request needs to specify a whole `item` or an `item_id` and an `edit` object with edition
instructions.

Edition instructions keys are operations names, and values are
operations parameters.

So far, the following operations are available:

- rotate (value are counter clockwise degrees)
- flip (value can be "vertical", "horizontal" or "both")
- brightness (value is a float)
- contrast (value is a float)
- saturation (value is a float)
- grayscale (value not used)

In the answer, the API will return an `item` object with updated
renditions.

Request example:

.. code:: javascript

    {"item": {...}, "edit": {"brightness": 1.1, "contrast": 1.2, "rotate": -90}}
