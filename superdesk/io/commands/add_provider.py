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
from superdesk import get_resource_service
from superdesk.errors import ProviderError


class AddProvider(superdesk.Command):
    """Add ingest provider.

    Example:
    ::

        $ python manage.py ingest:provider --provider='{"update_schedule" : { "minutes" : 5, "seconds" : 0 },
            "idle_time" : { "hours" : 0, "minutes" : 0 }, "content_expiry" : 2880, "name" : "aap-demo",
             "source" : "aap-demo", "feeding_service" : "rss",
             "config" : { "url" : "https://abcnews.go.com/abcnews/primetimeheadlines", "field_aliases" : [ ] },
             "feed_parser" : null, "content_types" : [ "text" ]}'

    """

    option_list = {
        superdesk.Option('--provider', '-p', dest='provider', required=True),
    }

    def run(self, provider):
        try:
            data = {}
            data = superdesk.json.loads(provider)
            data.setdefault('content_expiry', superdesk.app.config['INGEST_EXPIRY_MINUTES'])

            validator = superdesk.app.validator(superdesk.app.config['DOMAIN']['ingest_providers']['schema'],
                                                'ingest_providers')
            validation = validator.validate(data)

            if validation:
                get_resource_service('ingest_providers').post([data])
                return data
            else:
                ex = Exception('Failed to add Provider as the data provided is invalid. Errors: {}'
                               .format(str(validator.errors)))
                raise ProviderError.providerAddError(exception=ex, provider=data)
        except Exception as ex:
            raise ProviderError.providerAddError(ex, data)


superdesk.command('ingest:provider', AddProvider())
