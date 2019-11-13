# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from superdesk import get_resource_service
from superdesk.io import registry
from lxml import etree
import sys
from superdesk.metadata.item import ITEM_STATE


class ImportCommand(superdesk.Command):
    """Import articles into archives.

    Example:
    ::

        $ python manage.py xml:import ninjs data/sample.json

    """

    option_list = [
        superdesk.Option('parser', help="name of the feed parser"),
        superdesk.Option('path', help="path to the archive file to parse"),
        superdesk.Option('--profile', '-p', help="name of the profile to use (case sensitive"),
    ]

    def run(self, parser, path, profile):
        try:
            feed_parser = registry.registered_feed_parsers[parser]
        except KeyError:
            print("Can't find feed parser with this name")
            sys.exit(1)

        if profile is not None:
            content_types_service = get_resource_service("content_types")
            try:
                content_profile = content_types_service.find({'label': profile}).next()
            except StopIteration:
                print("Can't find content profile with this label")
                sys.exit(1)
            else:
                profile_id = content_profile['_id']

        with open(path, 'rb') as f:
            buf = f.read()
            buf = buf.replace(b'\r', b'&#13;')
            xml_parser = etree.XMLParser(recover=True)
            parsed = etree.fromstring(buf, xml_parser)
        articles = feed_parser.parse(parsed)
        updates = {ITEM_STATE: 'published'}
        if profile is not None:
            updates['profile'] = profile_id
        for article in articles:
            article.update(updates)
            article.setdefault('source', parser)
        archived_service = get_resource_service("archived")
        archived_service.post(articles)


superdesk.command('xml:import', ImportCommand())
