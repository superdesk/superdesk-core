.. _authentication:

Authentication
==============
This documentation explains the main mechanism of authentication.


Overview
--------
Main host mechanisms are located in :mod:`apps.auth`.  
Login is internally based on a token authentication: each user session is associated to a token.

There is a common access point, ``auth`` which can be used to log out, but to log in, each authentication mechanism use its own endpoint (``auth_db`` and ``auth_xmpp`` so far). This way each endpoint can use its own schema validation while the common endpoint can be called for logout, allowing several auth mechanisms to be running at the same time.

.. uml::

    title Authentication in Superdesk

    boundary client
    control "auth_**XXX**" as backend
    note right of backend
        auth_**XXX** service uses __auth__ datasource
    end note
    database datalayer

    backend <- client : **authenticate**\n(user credentials)

    alt success
        backend -> backend: //create token//
        backend -> datalayer: //create session//
        backend -> client: **user**\n(user name, token, user id)

    else bad credentials or failure
        backend -> client: HTTP error\n(401 or something else)

    end


Adding a new authentication mechanism
-------------------------------------

Adding a new authentication mechanism is done by creating a new endpoint extending the basic service. The new endpoint should be named **auth_XXX** where `XXX` is a short name for the new mechanism.

.. module:: apps.auth.service

The ``auth`` module provide the base features, with main service. 

.. autoclass:: AuthService
    :members:

To implement its authentication mechanism, a module need to override the `authenticate` method.

When creating a service based on `AuthService`, the authentication module must use the ``auth`` `datasource` instead of its own endpoint name. This allow several auth methods to use the same session system and to logout from ``auth`` common endpoint.

Special case: ``auth_db``
~~~~~~~~~~~~~~~~~~~~~~~~~
``auth_db`` is used for the basic database login/password authentication. In some cases it may be desirable to replace this mechanism (e.g. this is the case with LDAP). This is done by using the same endpoint name, and avoiding the import of :mod:`apps.auth.db` module. The login/pass default login interface in the client will then stay unchanged.


Other uses of :mod:`apps.auth`
------------------------------
Following functions can be used:

.. automodule:: apps.auth
    :members:

Superdesk OAuth
---------------

.. automodule:: superdesk.auth

Superdesk Google OAuth
----------------------

.. automodule:: superdesk.auth.oauth

Superdesk SAML Auth
-------------------

.. automodule:: superdesk.auth.saml

Superdesk OpenID Connect Auth
-----------------------------

.. automodule:: apps.auth.oidc
