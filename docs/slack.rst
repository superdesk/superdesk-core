Slack Link Previews
===================

.. versionadded:: 3.6

Superdesk can answer Slack's `Events API`_ so that links to Superdesk content pasted in Slack are
expanded into a rich preview. One Slack app is installed per Superdesk instance, and its bot posts
the previews through the ``chat.unfurl`` API, which means a preview is visible to everybody in the
channel where the link was shared. This first phase only implements the plumbing: the endpoint that
receives and verifies the Slack events, and the background task that will render the previews.
Rendering the previews and linking Slack users to Superdesk accounts come in later phases.

The endpoint used in Superdesk is ``/api/slack/events``. It answers ``404`` while
``SLACK_SIGNING_SECRET`` is unset, so an instance that has not configured a Slack app is unaffected.

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
