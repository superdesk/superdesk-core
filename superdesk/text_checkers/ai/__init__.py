# Copyright 2020 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError
from .. import tools
from .base import registered_ai_services, AIServiceBase
import superdesk

AUTO_IMPORT = True


class AIResource(Resource):
    schema = {
        'service': {
            'type': 'string',
            'required': True,
        },
        'item_id': {
            'type': 'string',
            'required': True,
        },
    }
    datasource = {
        'projection': {'analysis': 1}
    }
    internal_resource = False
    resource_methods = ['POST']
    item_methods = ['GET']


class AIService(BaseService):
    r"""Service managing article analysis with machine learning/AI related services

    When doing a POST request on this service, the following keys can be used (keys with a \* are required):


    ==========  ===========
    key         explanation
    ==========  ===========
    service \*  name of the service to use
    item_id \*  _id of the item in archive collection
    ==========  ===========

    e.g. to get autotagging with iMatrics service:

    .. sourcecode:: json

        {
            "service": "imatrics",
            "item_id": "some_id"
        }

    """

    def create(self, docs, **kwargs):
        # we override create because we don't want anything stored in database
        doc = docs[0]
        service = doc["service"]
        item_id = doc.get('item_id')
        try:
            service = registered_ai_services[service]
        except KeyError:
            raise SuperdeskApiError.notFoundError("{service} service can't be found".format(service=service))

        analyzed_data = service.analyze(item_id)
        docs[0].update({"analysis": analyzed_data})
        return [0]


def init_app(app):
    if AUTO_IMPORT:
        tools.import_services(app, __name__, AIServiceBase)

    endpoint_name = 'ai'
    service = AIService(endpoint_name, backend=superdesk.get_backend())
    AIResource.schema["service"]["allowed"] = list(registered_ai_services)
    AIResource(endpoint_name, app=app, service=service)
    superdesk.intrinsic_privilege(endpoint_name, method=['POST'])
