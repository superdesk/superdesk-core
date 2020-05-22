Authentication Server
=====================

Superdesk provides an OAuth2 authentication server for the `production API`_. The server is
using the `Client Credentials Grant`_ with JWT access token.

The endpoint used in Superdesk is ``/api/auth_server/token``.

.. _Client Credentials Grant: https://tools.ietf.org/html/rfc6749#section-4.4
.. _production API: production_api.html

Overview
--------

Here is the sequence of the authentication, which must entirely be done in HTTPS:

.. uml::

    title Authentication server flow in Superdesk (for third party clients)

    boundary client
    control "authentication server" as auth_server
    boundary "resource server\n(//Production API//)" as res_server

    client -> auth_server: request token
    note right
        using **client credentials** grant
        and **HTTP Basic Authentication**
    end note

    alt <color: green>success</color>
        client <- auth_server : **JWT** access token
        note right
            JWT payload contains the **client id**,
            the **expiration date**, and the **scope**
        end note
        loop
            client -> res_server: request with access token
            res_server -> res_server: validate **JWT** token signature, \nclient_id, expiration date and scope
            alt <color:green>valid token</color>
                client <- res_server: request answer
            else <color:DarkRed>invalid token (bad signature, expired token)</color>
                client <- res_server: HTTP 401 (Unauthorized) error
            else <color:DarkRed>invalid scope</color>
                client <- res_server: HTTP 403 (Forbidden) error
            end
        end

    else <color:DarkRed>failure</color>
        auth_server -> client: HTTP error\n(400 or something else)
        note right
            a //JSON// payload with ""error"" key should be present,
            the value being an explanation of the issue
        end note

    end

Settings
--------

The variables explained in the table below can be set, either as environment variable or
in ``settings.py``.

Please note that for ``AUTH_SERVER_SHARED_SECRET`` we recommend to use environment
variable instead of settings to limit attack surface if a malicious user gains access to
your settings.


============================  ========================================================
name                          explanation
============================  ========================================================
AUTH_SERVER_EXPIRATION_DELAY  delay in seconds when the access token is valid,
                              after this delay, a new token is needed.
                              Default to 86400 (1 day)
AUTH_SERVER_SHARED_SECRET     a secret shared with resource server to sign/validate
                              the access token. We recommend to set this value using
                              environment variable.
============================  ========================================================

Allowing a client
-----------------

A client needs to be registered with Superdesk authentication server.

You need to specify a *client id*, a *password* and the *scopes* allowed (see below).

This is done using ``python manage.py auth_server:register_client``, please check the
appropriate documentation in :ref:`cli` section.


Scope
-----

To interact with the production API, clients need to be explicitly allowed to perform
actions. This is done using the ``--scope`` argument when registering the client. The
possible values are:

================    ======================================================
permission          explanation
================    ======================================================
ARCHIVE_READ        The client can read items from archive collection
DESKS_READ          The client can get desks metadata
PLANNING_READ       The client can retrieve planning items
CONTACTS_READ       The client can get contacts metadata
USERS_READ          The client can retrieve users
ASSIGNMENTS_READ    The client can retrieve assignments
EVENTS_READ         The client can retrieve events
================    ======================================================

Access token
------------

If client is allowed, an access token is generated and can be used to access the desired
resources. The token is a `JSON Web Token`_ (JWT), which is signed, allowing the resource
server to verify it.

The payload of the token will contain the following keys:

=========  ====================================================================
key        explanation
=========  ====================================================================
client_id  id of the allowed client
iss        principal that issued the JWT, it's always ``Superdesk Auth Server``
iat        time when the JWT was issued (Unix time)
exp        expiration time (Unix time)
scope      list of allowed scopes (see above)
=========  ====================================================================

.. _JSON Web Token: https://tools.ietf.org/html/rfc7519

Security
--------

**All the traffic must be encrypted using HTTPS**.

The initial request is done by the client using `HTTP Basic Authentication`_, meaning the
password is going on the wire.

A salted hash of the client *password* is stored in superdesk, along with *client id* and
*scope*.

The JWT access token is not stored, it is only validated by resource server by checking its
signature.

The authorisation server and the resource server share a secret to sign and validate the
JWT Token. We recommend to use an environment variable instead of `settings.py` to set
this secret (the name of the variable is ``AUTH_SERVER_SHARED_SECRET``).

.. _HTTP Basic Authentication: https://tools.ietf.org/html/rfc7617

Testing
-------

By default, unsecured HTTP requests will be rejected. If you want to test authorisation
server with a local instance without HTTPS, you may set the ``AUTHLIB_INSECURE_TRANSPORT``
environment variable in the shell where server is started::

  $ export AUTHLIB_INSECURE_TRANSPORT=1

This is only for testing/development, **do NOT do that in production**.

To test locally a client token request, you can use curl:

.. code:: sh

    #!/bin/sh

    CLIENT_ID=0102030405060708090a0b0c
    CLIENT_SECRET=789101112
    URL=http://127.0.0.1:5000/api/auth_server/token

    curl -u ${CLIENT_ID}:${CLIENT_SECRET} -XPOST ${URL} -F grant_type=client_credentials

You can check Authlib_ documentation for more informations.

.. _Authlib: https://docs.authlib.org

CLI
---

You can manage tokens using Superdesk's CLI. Check ``auth_server:*`` commands at
:ref:`cli` for details.
