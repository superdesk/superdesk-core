Production API Server
=====================

Production API server is used to provide stable and versioned endpoints for third-party apps to consume news content
from Superdesk.


Overview
--------

Production API server uses the same DB and elastic search index as the main Superdesk app,
unlike Content API which has a separate DB.

Production API uses versioned endpoints to provide stable, non breaking changes API for third-party apps.
Current API version is **v1**


Endpoints
---------

Production API **v1** provides next endpoints:

- list all endpoints
    | path: **/prodapi/v1**
    | note: **upload** is not an endpoint actually, it is specified as a default empty domain in the settings to make assets work

- items list
    | path: **/prodapi/v1/items**
    | search backend: elastic
    | allowed methods: GET
    | query examples:

    - get all packages

    .. code::

            http://hostname/prodapi/v1/items?source={
                "query": {
                    "filtered": {
                        "filter": {
                            "terms": {
                                "type": ["composite"]
                            }
                        }
                    }
                }
            }


    - specify a desk(s)


    .. code::

            http://hostname/prodapi/v1/items?source={
                "query": {
                    "filtered": {
                        "filter": {
                            "terms": {
                                "task.desk": ["5c489481405ecc015e5e10bc"]
                            }
                        }
                    }
                }
            }


    - specify an Assignment(s)


    .. code::

            http://hostname/prodapi/v1/items?source={
                "query": {
                    "bool": {
                        "must": {
                            "terms": {
                                "assignment_id": ["60e403bc8361feb5664719b1"]
                            }
                        }
                    }
                }
            }

- item details
    | path: **/prodapi/v1/items/<guid>**
    | allowed methods: GET

- item HATEOAS:
    | **assignment**: Associated `Assignment`_
    | **planning**: Associated `Planning`_
    | **event**: Associated `Event`_
    | Example:

    .. code::

        "_links": {
            "assignment": {
                "title": "Assignment",
                "href": "assignments/60e403bc8361feb5664719b1",
                "state": "in_progress",
                "scheduled": "2021-07-07T02:00:00+0000",
                "content_type": "text",
            },
            "planning": {
                "title": "Planning",
                "href": "planning/60e6a115de25009b39121d7f"
            },
            "event": {
                "title": "Event",
                "href": "events/60e6a116de25009b39121d80"
            }
        }


- desks list
    | path: **/prodapi/v1/desks**
    | search backend: mongo
    | allowed methods: GET
    | query examples:

    - filter by ``name``

    .. code::

            http://hostname/prodapi/v1/desks?where={"name": "Production"}

- desks details
    | path: **/prodapi/v1/desks/<_id>**
    | allowed methods: GET

- assignments list
    | path: **/prodapi/v1/assignments**
    | search backend: elastic
    | allowed methods: GET

- assignments details
    | path: **/prodapi/v1/assignments/<_id>**
    | allowed methods: GET

- assignments HATEOAS:
    | **planning**: Associated `Planning`_
    | **event**: Associated `Event`_
    | **content**: List of `Content`_
    | Example:

    .. code::

        "_links": {
            "planning": {
                "title": "Planning",
                "href": "planning/60e6a115de25009b39121d7f"
            },
            "event": {
                "title": "Event",
                "href": "events/60e6a116de25009b39121d80"
            },
            "content": [
                {
                    "title": "Item",
                    "href": "items/60e6a257de25009b39121d81",
                    "state": "published",
                    "pubstatus": "usable"
                }
            ]
        }

- planning list
    | path: **/prodapi/v1/planning**
    | search backend: elastic
    | allowed methods: GET

- planning details
    | path: **/prodapi/v1/planning/<guid>**
    | allowed methods: GET

- planning HATEOAS:
    | **assignments**: List of `Assignment`_
    | **event**: Associated `Event`_
    | Example:

    .. code::

        "_links": {
            "assignments: [
                {
                    "title": "Assignment",
                    "href": "assignments/60e403bc8361feb5664719b1",
                    "state": "in_progress",
                    "scheduled": "2021-07-07T02:00:00+0000",
                    "content_type": "text",
                }
            ],
            "event": {
                "title": "Event",
                "href": "events/60e6a116de25009b39121d80"
            }
        }

- events list
    | path: **/prodapi/v1/events**
    | search backend: elastic
    | allowed methods: GET

- events details
    | path: **/prodapi/v1/events/<guid>**
    | allowed methods: GET

- events HATEOAS
    | **assignments**: List of `Assignment`_
    | **plannings**: List of `Planning`_
    | Example:

    .. code::

        "_links": {
            "assignments": [
                {
                    "title": "Assignment",
                    "href": "assignments/60e403bc8361feb5664719b1",
                    "state": "in_progress",
                    "scheduled": "2021-07-07T02:00:00+0000",
                    "content_type": "text",
                }
            ],
            "plannings": [
                {
                    "title": "Planning",
                    "href": "planning/60e6a115de25009b39121d7f"
                }
            ]
        }

- event files list
    | path: **/prodapi/v1/events_files**
    | search backend: mongo
    | allowed methods: GET

- event files details
    | path: **/prodapi/v1/events_files/<_id>**
    | allowed methods: GET

- events history list
    | path: **/prodapi/v1/events_history**
    | search backend: mongo
    | allowed methods: GET

- events history details
    | path: **/prodapi/v1/events_history/<_id>**
    | allowed methods: GET

- users list
    | path: **/prodapi/v1/users**
    | search backend: mongo
    | allowed methods: GET

- users details
    | path: **/prodapi/v1/users/<_id>**
    | allowed methods: GET

- contacts list
    | path: **/prodapi/v1/contacts**
    | search backend: elastic
    | allowed methods: GET

- contacts details
    | path: **/prodapi/v1/contacts/<_id>**
    | allowed methods: GET

- media assets
    | path: **/prodapi/v1/assets/MEDIA_ID.jpg**
    | example: http://hostname/prodapi/v1/assets/5d22f47e5589a98f90775752.jpg


HATEOAS
-------
HATEOAS (Hypermedia as the Engine of Application State) is provided in the results
to link items to other resources, as well as provide other relevant information about the link.

This section provides the possible types of HATEOAS links, and their available metadata.

Assignment
^^^^^^^^^^
Provides a link to the associated Assignment

Attributes:

=======================  ===============  ===========================================================================
Name                     Type             Description
=======================  ===============  ===========================================================================
**title**                string           Name of the Assignment resource
**href**                 string           The URL to the resource item
**state**                | draft          The ``state`` of the Assignment
                         | assigned
                         | in_progress
                         | completed
                         | submitted
                         | cancelled
**scheduled**            datetime         The date & time the Assignment is due
**content_type**         g2_content_type  Qcode of the type of content expected
**content_href**         string           The URL to the content (if any)
**content_state**        draft            The ``state`` (as defined in :ref:`schema`) of the associated content
**content_pubstatus**    string           The ``pubstatus`` (as defined in :ref:`schema`) of the associated content
=======================  ===============  ===========================================================================

Example

.. code::

    "_links": {
        "assignment": {
            "title": "Assignment",
            "href": "assignments/60e403bc8361feb5664719b1",
            "state": "in_progress",
            "scheduled": "2021-07-07T02:00:00+0000",
            "content_type": "text",
            "content_state": "published",
            "content_pubstatus": "usable"
        }
    }

Planning
^^^^^^^^
Provides a link to the associated Planning item

Attributes:

============  ===============  ===========================================================================
Name          Type             Description
============  ===============  ===========================================================================
**title**     string           Name of the Planning resource
**href**      string           The URL to the resource item
============  ===============  ===========================================================================

Example

.. code::

    "_links": {
        "planning": {
            "title": "Planning",
            "href": "planning/60e6a115de25009b39121d7f"
        }
    }

Event
^^^^^
Provides a link to the associated Event

Attributes:

============  ===============  ===========================================================================
Name          Type             Description
============  ===============  ===========================================================================
**title**     string           Name of the Event resource
**href**      string           The URL to the resource item
============  ===============  ===========================================================================

Example:

.. code::

    "_links": {
        "event": {
            "title": "Event",
            "href": "events/60e6a116de25009b39121d80"
        }
    }

Content
^^^^^^^
Provides an array of linked Content

Attributes:

===============  ===============  ===========================================================================
Name             Type             Description
===============  ===============  ===========================================================================
**title**        string           Name of the News Content resource
**href**         string           The URL to the resource item
**state**        draft            The ``state`` (as defined in :ref:`schema`) of the associated content
**pubstatus**    string           The ``pubstatus`` (as defined in :ref:`schema`) of the associated content
===============  ===============  ===========================================================================

Example:

.. code::

    "_links": {
        "content": [
            {
                "title": "Item",
                "href": "items/60e6a257de25009b39121d81",
                "state": "published",
                "pubstatus": "usable"
            }
        ]
    }


Authentication
--------------

Production API implements JWT token authentication.
Third-party apps must retrieve token using AuthServer_ and provide it with every request.

.. _AuthServer: https://superdesk.readthedocs.io/en/latest/auth_server.html

Example::

  export PRODAPI=http://127.0.0.1:5500/prodapi/v1
  export JWT_TOKEN=your.jwt.token
  export FILTER=source='{"query":{"filtered":{"filter":{"terms":{"type":["text"]}}}}}'
  curl -g -i $PRODAPI/items?$FILTER -H "Authorization: Bearer $JWT_TOKEN"
  
Authorization
-------------

Every resource in production API defines a list of scopes required to have access to a certain method.
You can read more about scopes here_

.. _here: https://superdesk.readthedocs.io/en/latest/auth_server.html#scope


Testing
-------

Production API uses pytest_ as a test framework.

.. _pytest: https://docs.pytest.org/

pytest-env_ plugin is used to allow defining environment variables.

.. _pytest-env: https://pypi.org/project/pytest-env/

nose-exclude_ plugin was used to avoid running pytest related test cases with nosetests (test framework which runs unit-tests in superdesk-core).

.. _nose-exclude: https://pypi.org/project/nose-exclude/

To run tests for production API, execute ``pytest`` command from ``prod_api`` folder.

All fixtures for production API tests are defined in the ``conftest.py`` file.
Tests for authentication and authorization are in ``test_auth.py`` file and they are more like e2e.
To test an entire auth process close to real interaction between client, auth server and production API,
2 flask apps are required respectively.

.. note::
    To avoid spinning 2 flask servers (superdesk and prod api) in separate processes and send real requests via local
    network to test things, flask's built-in test client was used.
    It requires having 2 flask apps/clients in one test case (fixtures).
    The issue is that 2 flask apps in the same process will conflict with each other
    (flask registers resources simply in a variable, so one flask app will overwrite resources of another app),
    to avoid this issue, only one flask app must be active at a period of time.


Settings
--------

Environment variables for configuration:

============================  ========================================================
name                          explanation
============================  ========================================================
PRODAPI_URL                   Production API url.
                              Set this when running api behind a proxy.
                              Default: ``http://localhost:5500``

PRODAPI_URL_PREFIX            Url prefix.
                              Default: ``prodapi``

MEDIA_PREFIX                  Prefix used to generate media assets url.
                              Default: ``http://localhost:5500/prodapi/v1/assets``

AUTH_SERVER_SHARED_SECRET     A secret shared with auth server to sign/validate
                              the access token.
                              Default: ``''``

PRODAPI_AUTH_ENABLED          Enable authentication for production API
                              Default: ``True``
============================  ========================================================

Rest of the settings are comes from Superdesk configuration_:

.. code::

    DEBUG,
    SUPERDESK_TESTING,
    MONGO_URI,
    ELASTICSEARCH_INDEX,
    ELASTICSEARCH_URL,
    AMAZON_ACCESS_KEY_ID,
    AMAZON_SECRET_ACCESS_KEY,
    AMAZON_REGION,
    AMAZON_CONTAINER_NAME,
    AMAZON_S3_SUBFOLDER,
    AMAZON_OBJECT_ACL,
    AMAZON_ENDPOINT_URL

.. _configuration: https://superdesk.readthedocs.io/en/latest/settings.html#configuration