# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import hashlib
import logging
import email.policy

from datetime import timedelta
from superdesk.utc import utcnow
from superdesk.lock import lock, unlock
from bson.json_util import dumps
from flask_mail import Message
from superdesk.celery_app import celery
from flask import current_app as app, render_template, render_template_string
from superdesk import get_resource_service

logger = logging.getLogger(__name__)


class SuperdeskMessage(Message):

    def as_bytes(self):
        msg = self._message()
        return msg.as_bytes(policy=email.policy.HTTP)


EMAIL_TIMESTAMP_RESOURCE = 'email_timestamps'


@celery.task(bind=True, max_retries=3, soft_time_limit=120)
def send_email(self, subject, sender, recipients, text_body, html_body, cc=None, bcc=None):
    _id = get_activity_digest({
        'subject': subject,
        'recipients': recipients,
        'text_body': text_body,
        'html_body': html_body,
        'cc': cc,
        'bcc': bcc,
    })

    lock_id = 'email:%s' % _id
    if not lock(lock_id, expire=120):
        return

    try:
        msg = SuperdeskMessage(subject, sender=sender, recipients=recipients, cc=cc, bcc=bcc,
                               body=text_body, html=html_body)
        return app.mail.send(msg)
    finally:
        unlock(lock_id, remove=True)


def send_activate_account_email(doc, activate_ttl):
    user = get_resource_service('users').find_one(req=None, _id=doc['user'])
    first_name = user.get('first_name')
    app_name = app.config['APPLICATION_NAME']
    admins = app.config['ADMINS']
    client_url = app.config['CLIENT_URL']
    url = '{}/#/reset-password?token={}'.format(client_url, doc['token'])
    hours = activate_ttl * 24
    subject = render_template("account_created_subject.txt", app_name=app_name)
    text_body = render_template("account_created.txt", app_name=app_name, user=user,
                                first_name=first_name, instance_url=client_url, expires=hours, url=url)
    html_body = render_template("account_created.html", app_name=app_name, user=user,
                                first_name=first_name, instance_url=client_url, expires=hours, url=url)
    send_email.delay(subject=subject, sender=admins[0], recipients=[doc['email']],
                     text_body=text_body, html_body=html_body)


def send_user_status_changed_email(recipients, status):
    admins = app.config['ADMINS']
    app_name = app.config['APPLICATION_NAME']
    subject = render_template("account_status_changed_subject.txt", app_name=app_name, status=status)
    text_body = render_template("account_status_changed.txt", app_name=app_name, status=status)
    html_body = render_template("account_status_changed.html", app_name=app_name, status=status)
    send_email.delay(subject=subject, sender=admins[0], recipients=recipients,
                     text_body=text_body, html_body=html_body)


def send_reset_password_email(doc, token_ttl):
    admins = app.config['ADMINS']
    client_url = app.config['CLIENT_URL']
    app_name = app.config['APPLICATION_NAME']
    url = '{}/#/reset-password?token={}'.format(client_url, doc['token'])
    hours = token_ttl * 24
    subject = render_template("reset_password_subject.txt")
    text_body = render_template("reset_password.txt", email=doc['email'], expires=hours, url=url, app_name=app_name)
    html_body = render_template("reset_password.html", email=doc['email'], expires=hours, url=url, app_name=app_name)
    send_email.delay(subject=subject, sender=admins[0], recipients=[doc['email']],
                     text_body=text_body, html_body=html_body)


def send_user_mentioned_email(recipients, user_name, doc, url):
    logging.info('sending mention email to: %s', recipients)
    admins = app.config['ADMINS']
    app_name = app.config['APPLICATION_NAME']
    subject = render_template("user_mention_subject.txt", username=user_name)
    text_body = render_template("user_mention.txt", text=doc['text'], username=user_name, link=url, app_name=app_name)
    html_body = render_template("user_mention.html", text=doc['text'], username=user_name, link=url, app_name=app_name)
    send_email.delay(subject=subject, sender=admins[0], recipients=recipients,
                     text_body=text_body, html_body=html_body)


def get_activity_digest(value):
    h = hashlib.sha1()
    json_encoder = app.data.json_encoder_class()
    h.update(dumps(value, sort_keys=True,
                   default=json_encoder.default).encode('utf-8'))
    return h.hexdigest()


def send_activity_emails(activity, recipients):
    now = utcnow()
    message_id = get_activity_digest(activity)
    # there is no resource for email timestamps registered,
    # so use users resoure to get pymongo db
    email_timestamps = app.data.mongo.pymongo('users').db[EMAIL_TIMESTAMP_RESOURCE]
    last_message_info = email_timestamps.find_one(message_id)
    resend_interval = app.config.get('EMAIL_NOTIFICATION_RESEND', 24)

    if last_message_info and last_message_info['_created'] + timedelta(hours=resend_interval) > now:
        return

    admins = app.config['ADMINS']
    app_name = app.config['APPLICATION_NAME']
    notification = render_template_string(activity.get('message'), **activity.get('data'))
    text_body = render_template("notification.txt", notification=notification, app_name=app_name)
    html_body = render_template("notification.html", notification=notification, app_name=app_name)
    subject = render_template("notification_subject.txt", notification=notification)
    send_email.delay(subject=subject, sender=admins[0], recipients=recipients,
                     text_body=text_body, html_body=html_body)
    email_timestamps.update({'_id': message_id}, {'_id': message_id, '_created': now}, upsert=True)


def send_article_killed_email(article, recipients, transmitted_at):
    admins = app.config['ADMINS']
    app_name = app.config['APPLICATION_NAME']
    place = next(iter(article.get('place') or []), '')
    if place:
        place = place.get('qcode', '')
    body = article.get('body_html', '')
    subject = article.get('headline', 'Kill Notification')

    text_body = render_template("article_killed.txt", app_name=app_name, place=place, body=body)
    html_body = render_template("article_killed.html", app_name=app_name, place=place, body=body)

    send_email.delay(subject=subject, sender=admins[0], recipients=recipients,
                     text_body=text_body, html_body=html_body)
