# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
import json
from eve.utils import ParsedRequest, config


class DeleteArchivedDocumentCommand(superdesk.Command):
    """
    Deletes a Text Archive document(s) from both Mongodb and ElasticSearch.

    It deletes digital package and the story given by id.
    It accepts one or more ids separated by space.

    Example:
    ::

        $ manage.py app:deleteArchivedDocument 588c1df11d41c80928015601 588c1b901d41c805dce70df0

    """

    capture_all_args = True

    def can_delete_items(self, items):
        """Checks if the given items are deletable"""

        archived_service = superdesk.get_resource_service('archived')
        can_delete = True
        messages = []

        for item in items:
            try:
                archived_service.validate_delete_action(item, True)
            except Exception as ex:
                can_delete = False
                messages.append('-' * 45)
                messages.append('Cannot delete {} as {}'.format(item['item_id'], str(ex)))

        if not can_delete:
            [print(m) for m in messages]

        return can_delete

    def get_archived_items(self, ids):
        """Returns the items with the given list of ids"""

        query = {
            'query': {
                'filtered': {
                    'filter': {
                        'and': [
                            {'terms': {'_id': ids}}
                        ]
                    }
                }
            }
        }

        request = ParsedRequest()
        request.args = {'source': json.dumps(query)}
        return list(superdesk.get_resource_service('archived').get(req=request, lookup=None))

    def delete(self, items):
        """Deletes the given items and any digital package of them"""

        archived_service = superdesk.get_resource_service('archived')
        for item in items:
            articles_to_kill = archived_service.find_articles_to_kill({'_id': item[config.ID_FIELD]}, False)

            if not articles_to_kill:
                continue

            for article in articles_to_kill:
                archived_service.command_delete({'_id': article[config.ID_FIELD]})
                print("Deleted item {} ".format(article[config.ID_FIELD]))

    def run(self, ids):
        if ids and len(ids) > 0:
            items = self.get_archived_items(ids)

            if not items:
                print("No archived story found with given ids(s)!")
                return

            if self.can_delete_items(items):
                self.delete(items)
                print("Delete has been completed")

        else:
            print("Please provide at least one id!")
            return


superdesk.command('app:deleteArchivedDocument', DeleteArchivedDocumentCommand())
