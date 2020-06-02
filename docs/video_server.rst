Video server
============

`HTTP API video editor <https://github.com/superdesk/video-server-app>`_ with pluggable file storages, video editing backends, and streaming capabilities.
When configured, Superdesk uses video server to edit, store and read video files.


Settings
--------

Environment variables for configuration:

============================  ========================================================
name                          explanation
============================  ========================================================
VIDEO_SERVER_URL              Video server API url.
                              Default: ``http://localhost:5050``

VIDEO_SERVER_ENABLED          Enable video server.
                              Default: ``False``
============================  ========================================================
