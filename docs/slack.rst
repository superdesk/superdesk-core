Slack Link Previews
===================

.. versionadded:: 3.6

Superdesk can answer Slack's `Events API`_ so that links to Superdesk content pasted in Slack are
expanded into a rich preview. One Slack app is installed per Superdesk instance, and its bot posts
the previews through the ``chat.unfurl`` API, which means a preview is visible to everybody in the
channel where the link was shared. A preview is only produced for a Slack user who is linked to a
Superdesk account, see `Account linking`_ below. What ends up in a preview is explained in
`How previews are decided`_.

The endpoints used in Superdesk live under ``/api/slack/``, the Slack app itself only talks to
``/api/slack/events``. They all answer ``404`` while ``SLACK_SIGNING_SECRET`` is unset, so an
instance that has not configured a Slack app is unaffected.

.. _Events API: https://docs.slack.dev/apis/events-api/

Settings
--------

The variables explained in the table below can be set, either as environment variable or in
``settings.py``. We recommend to set ``SLACK_SIGNING_SECRET`` and ``SLACK_BOT_TOKEN`` using
environment variables, to limit the attack surface if a malicious user gains access to your
settings.

=====================  =========================================================
name                   explanation
=====================  =========================================================
SLACK_SIGNING_SECRET   Slack app signing secret, used to verify the requests
                       Slack sends to the server. The Slack module is inert
                       unless this is set, and the events endpoint answers 404.
SLACK_BOT_TOKEN        Bot user OAuth token, used to call the Slack API to post
                       the unfurls.
SLACK_TEAM_ID          Optional. If set, events coming from other Slack
                       workspaces are ignored.
SLACK_APP_ID           Optional. If set, events coming from other Slack apps are
                       ignored.
=====================  =========================================================

Creating the Slack app
----------------------

On https://api.slack.com/apps, choose *Create New App* then *From an app manifest*, pick the
workspace and paste the manifest below. Replace ``<your-superdesk-server>`` with the public host of
your Superdesk server and ``<your-superdesk-client>`` with the host of your ``CLIENT_URL``.

.. code-block:: yaml

    display_information:
      name: Superdesk
      description: Rich previews for Superdesk links shared in Slack
    features:
      bot_user:
        display_name: Superdesk
        always_online: false
      unfurl_domains:
        - <your-superdesk-client>
    oauth_config:
      scopes:
        bot:
          - links:read
          - links:write
          - chat:write
    settings:
      event_subscriptions:
        request_url: https://<your-superdesk-server>/api/slack/events
        bot_events:
          - link_shared
      org_deploy_enabled: false
      socket_mode_enabled: false
      token_rotation_enabled: false

The request URL must be publicly reachable over HTTPS: Slack sends a ``url_verification`` challenge
to it while you save the manifest, and refuses the app if it does not get a valid answer within
three seconds.

Only links whose domain is listed in ``unfurl_domains`` reach the app, and the domain must be one
your workspace controls, so this is the Superdesk client host rather than the API host.

After creating the app, install it in the workspace, then copy:

* *OAuth & Permissions* > *Bot User OAuth Token* (starts with ``xoxb-``) into ``SLACK_BOT_TOKEN``
* *Basic Information* > *App Credentials* > *Signing Secret* into ``SLACK_SIGNING_SECRET``

Restart the ``rest`` and ``work`` processes for the new settings to take effect. App unfurls do not
require the bot to be a member of the channel; if previews do not show up in a private channel,
inviting the bot (``/invite @Superdesk``) is the first thing to try.

.. _Account linking:

Account linking
---------------

Superdesk only renders a preview for a Slack user who has been linked to a Superdesk account. The
link says "this Slack user is that Superdesk user", and the preview is then built with that user's
permissions. Links are stored in the ``slack_user_links`` collection, which the server writes on
its own: there is no REST endpoint for it, and users cannot create a link through the API. A Slack
user and a Superdesk user can each take part in at most one link.

Running ``python manage.py app:initialize_data`` creates the two unique indexes of the collection,
one over ``team_id`` and ``slack_user_id``, the other over ``team_id`` and ``user``.

Linking in the browser
~~~~~~~~~~~~~~~~~~~~~~

When an unlinked Slack user shares a Superdesk link, the bot answers with an ephemeral message
holding a one-time URL, ``<SERVER_URL>/slack/link?t=<token>``. The token is random, lives in Redis
for ten minutes and only names the Slack side of the link (workspace, Slack user and the channel
the prompt was sent to).

Opening that URL in the browser where the user is already logged into Superdesk gives the server
both sides: the Slack side from the token, the Superdesk side from the session. Superdesk sets a
``session_token`` cookie on every authenticated API request, and the token authentication accepts
that cookie when there is no ``Authorization`` header. This assumes the client and the API are
served from the same host, which is the usual production setup, because the cookie is
``SameSite=Lax`` and is only sent to its own site. When they are not, use the CLI instead.

Three endpoints implement the flow, all of them plain HTML pages, none of them used by the
Superdesk client:

===================================  =========================================================
endpoint                             what it does
===================================  =========================================================
``GET /api/slack/link?t=<token>``    Shows who would be linked to whom and a *Connect* button.
                                     Redirects to ``CLIENT_URL`` when there is no session, so
                                     the user can log in and click the button in Slack again.
``POST /api/slack/link``             Creates the link, consumes the token and tells the Slack
                                     user about it.
``/api/slack/link/disconnect``       Removes the link of the logged in user, ``GET`` asks for
                                     confirmation and ``POST`` performs the removal.
===================================  =========================================================

The two mutations are ``POST`` requests carrying a nonce from the signed session cookie, because a
``GET`` that mutates would be triggerable from any other site: ``SameSite=Lax`` still sends the
session cookie on a top level navigation.

No OAuth is involved anywhere, and the flow only works in one direction. The endpoints read a
Superdesk session that already exists, they never create one, so Slack cannot log anybody into
Superdesk, and a link never grants access to a Superdesk account.

Linking from the command line
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The same links can be managed by an administrator, which is also the way out when the client and
the API are not on the same host. The Slack user id is the one starting with ``U``, visible under
*View full profile* > *Copy member ID* in Slack.

.. code-block:: bash

    $ python manage.py slack:link_user --user jdoe --slack-user U012ABCDEF
    $ python manage.py slack:link_user --user jdoe --slack-user U012ABCDEF --team T012ABCDEF
    $ python manage.py slack:unlink_user --user jdoe
    $ python manage.py slack:list_links

``--team`` defaults to ``SLACK_TEAM_ID`` and is required when that setting is empty. The commands
fail with a non zero exit code when the user does not exist, or when either side of the link is
already taken by somebody else.

.. _How previews are decided:

How previews are decided
------------------------

Every ``link_shared`` event is handled the same way, one link at a time:

1. The Slack user who shared the link is looked up in ``slack_user_links``. Without a link nothing
   is resolved and the bot answers with the connect prompt described above.
2. The URL is resolved to an entity. Only URLs on the ``CLIENT_URL`` host that a handler
   recognises are considered, anything else is dropped without a word to Slack.
3. The entity is loaded, and the visibility check runs the same search Superdesk itself runs, as
   the linked user. It goes through the same filters as the monitoring and search views, so a
   preview never shows an item the user could not open in Superdesk.
4. The external preview policy decides how much of the entity may leave Superdesk, because the
   preview is read by everybody in the channel and not only by the person who shared the link.
5. What is left is rendered as a Block Kit card and posted with ``chat.unfurl``.

There are three possible outcomes:

* a full card with the metadata listed below,
* a generic *Details are restricted* card, naming only the item type, for an item under a future
  embargo, marked for legal or not for publication, or in a spiked, killed or recalled state,
* nothing at all, when the item does not exist or the linked user would not see it in Superdesk.
  The link stays a plain link in Slack, which does not tell the channel whether the item exists.

A full card shows the headline (falling back to the slugline), the item type and state, the desk
and stage, the author and the slugline, the time of the last version, and a link back to
Superdesk. It never shows the body, the abstract or description, editorial notes, the SMS text,
embargo or publish schedule dates, the item flags, or who holds the lock. These fields are not
merely skipped by the renderer: the preview is built from an allow list of item fields, so a field
that is not on the list cannot reach Slack.

Because ``chat.unfurl`` posts into the channel, a preview is visible to everybody who can read that
channel, including people with no Superdesk account. It is decided by the permissions of the person
who pasted the link, the way forwarding a screenshot would be.

When the sharing Slack user is not linked yet, the event is kept in Redis for ten minutes. Once
they connect their account through the prompt, that event is replayed automatically and the preview
appears under the message they already sent, so there is no need to paste the link again.
