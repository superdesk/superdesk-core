# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json

from flask import current_app as app
from superdesk.emails import send_email
from superdesk.publish import register_transmitter
from superdesk.publish.publish_service import PublishService
from superdesk.errors import PublishEmailError
from superdesk.media.media_operations import get_watermark
from flask_mail import Attachment
from PIL import Image
import io
import logging

errors = [PublishEmailError.emailError().get_error_description()]

logger = logging.getLogger(__name__)


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
            except Exception:
                item = {}

            admins = app.config['ADMINS']
            recipients = [r.strip() for r in config.get('recipients', '').split(';') if r.strip()]
            bcc = [r.strip() for r in config.get('recipients_bcc', '').split(';') if r.strip()]
            if not recipients and not bcc:
                raise PublishEmailError.recipientNotFoundError(LookupError('recipient and bcc fields are empty!'))

            subject = item.get('message_subject', 'Story: {}'.format(queue_item['item_id']))
            text_body = item.get('message_text', queue_item['formatted_item'])
            html_body = item.get('message_html', queue_item['formatted_item'])

            # Attach feature media if required
            attachments = []
            if config.get('attach_media') and item.get('renditions'):
                # The CID can be used to embbed the image in the html template email like <img src=CID:cid-value>
                cid = config.get('media_cid', '')
                # Get the rendition that has been nominated for attaching to the email
                rendition = config.get('media_rendition', '')
                media_item = item.get('renditions', {}).get(rendition)
                if media_item and rendition:
                    media = app.media.get(media_item['media'], resource='upload')
                    im = Image.open(media)
                    if config.get('watermark', False):
                        im = get_watermark(im)

                    binary = io.BytesIO()
                    im.save(binary, 'jpeg', quality=80)

                    attachments.append(Attachment(filename=media.name, content_type=media.content_type,
                                                  data=binary.getvalue(),
                                                  headers=[('Content-ID', cid)]))

            # sending email synchronously
            send_email(subject=subject,
                       sender=admins[0],
                       recipients=recipients,
                       text_body=text_body,
                       html_body=html_body,
                       bcc=bcc,
                       attachments=attachments)

        except Exception as ex:
            raise PublishEmailError.emailError(ex, queue_item.get('destination'))


register_transmitter('email', EmailPublishService(), errors)
