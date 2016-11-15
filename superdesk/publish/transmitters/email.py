# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.emails import send_email
from flask import current_app as app
from superdesk.publish import register_transmitter
from superdesk.publish.publish_service import PublishService
from superdesk.errors import PublishEmailError
import json
errors = [PublishEmailError.emailError().get_error_description()]


class EmailPublishService(PublishService):
    """Email Transmitter

    Works only with email formatter.

    :param recipients: email addresses separated by ``;``
    """

    def _transmit(self, queue_item, subscriber):
        config = queue_item.get('destination', {}).get('config', {})

        try:
            # detect if it's been formatted by the Email formatter, is so load the item
            try:
                item = json.loads(queue_item['formatted_item'])
                if 'message_subject' not in item:
                    item = {}
            except:
                item = {}

            if not config.get('recipients'):
                raise PublishEmailError.recipientNotFoundError(LookupError('recipient field not found!'))

            admins = app.config['ADMINS']
            recipients = config.get('recipients').rstrip(';').split(';')

            subject = item.get('message_subject', 'Story: {}'.format(queue_item['item_id']))
            text_body = item.get('message_text', queue_item['formatted_item'])
            html_body = item.get('message_html', queue_item['formatted_item'])

            # sending email synchronously
            send_email(subject=subject,
                       sender=admins[0],
                       recipients=recipients,
                       text_body=text_body,
                       html_body=html_body)

        except Exception as ex:
            raise PublishEmailError.emailError(ex, queue_item.get('destination'))


register_transmitter('email', EmailPublishService(), errors)
