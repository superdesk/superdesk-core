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
For video mapping, ``Rights`` and ``Credit`` also supply ``CopyrightNotice`` and
``CreditLine`` defaults when those canonical keys are absent. ``raw_metadata`` remains
unchanged, and configured mappings can still reference the original video keys.
``iptc_metadata`` is a separate payload for client ``iptcMapping`` extensions, using
ExifTool IPTC names (for example ``ObjectName``, ``By-line`` and ``SubjectReference``).
It includes vocabulary, location, language and date tags omitted by the canonical reader,
preserves list values, and uses XMP equivalents when IPTC tags are absent. Pictures prefer
IPTC values; videos use XMP. XMP creation timestamps also supply ``TimeCreated``.
Both payloads are derived from a single ExifTool extraction of the temporary file;
canonical picture fields retain their XMP names, defaults and creator-list representation.
Pictures that previously required the pyexiv2 fallback now use that same consistent
picture-field shape rather than the fallback's sparse fields and scalar creator.
The client runs extension hooks sequentially, once per file, passing the mapped article
and upload parent. Hooks finish before metadata becomes editable or saveable; failures
are reported and block committing that file. Subsequent status refreshes do not rerun hooks
or overwrite user edits.
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
Confirmation cannot replace the binary: PATCH requests containing ``media`` are rejected.
The worker then performs video server upload/timeline generation if configured.
Other processing states are ``pending``, ``processing``, ``ready``, and ``failed``.
A rendition failure includes an ``error`` message; discard the file and upload it again.
Worker cancellation during processing also records failure and notifies the client
before propagating cancellation, rather than leaving the upload stuck in ``processing``.
Claim acquisition is covered by the same recovery: a unique worker token is written
atomically with ``processing``. If the claim response is lost or cancelled, recovery
uses that token to reconcile the result and record failure without changing or
cleaning up another worker's claim.
Processing updates are persisted in MongoDB: this flow does not store or retrieve Celery task results.
Each worker state change refreshes ``_updated`` and ``_etag`` atomically with the data,
so conditional GETs after a notification return the new metadata or renditions.

Once ready, ``POST /archive`` with ``staged_id`` and the edited article fields. The server
reuses the stored binary and renditions without waiting for a worker. A premature commit
returns HTTP 409. Staged files are owner-restricted and can be committed only once.
Mapped metadata supplies defaults for missing article fields. For an ``extra`` dictionary,
missing custom subfields are filled individually; explicitly supplied values, including
empty strings and null values, are preserved.
Before archive creation, staging enters ``committing`` and reserves an archive ID.
If validation or insertion fails, retry the same ``staged_id``: it reuses that ID,
preventing concurrent retries from creating duplicate items. Staging is finalized only
after archive persistence, never during the pre-create hook.
Expiry cleanup reconciles unfinished commits with the archive,
preserving media belonging to items already persisted when cleanup checks.
The client allows Upload confirmation while renditions are still running, waits for the
ready notification, and commits automatically without requiring another click.

Removing an upload from the client queue is local only: stop polling and do not send
a DELETE request. Staging does not support DELETE. Processing continues, and abandoned
uploads and their persisted media remain until expiry. Workers still clean up temporary
files and unpublished output.
Worker updates may invalidate ``If-Match`` between a GET and confirmation; clients should
fetch a fresh, uncached snapshot before retrying a confirmation that returns HTTP 412.

``UPLOAD_STAGING_TTL`` defaults to six hours. Celery beat schedules
``apps.archive.upload_staging.expire_staged_uploads`` every five minutes to remove expired
uploads and their media. Media-processing tasks have a ten-minute soft runtime limit and
a fifteen-minute hard runtime limit; these do not limit archive creation in HTTP requests
or serialize it with expiry cleanup.
A worker and beat must be running; no Celery results backend is
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
