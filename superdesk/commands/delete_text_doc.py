import superdesk
import json


class DeleteDocCommand(superdesk.Command):
    """
    Delete a Text Archive document from both Mongodb and ElasticSearch by supplying a GUID

    manage.py app:deletedoc
        -i urn:newsml:localhost:2016-09-05T11:54:49.869091:6bdbd02b-f6c5-46d3-bc53-4c1fc74252af
    """

    option_list = [
        superdesk.Option('--guid', '-i', dest='guids', action='append',
                         help='pass guids for articles to delete'),
        superdesk.Option('--file', '-f', dest='file'),
    ]

    def bulk_delete(self, guids):
        archived_service = superdesk.get_resource_service('archived')
        # checks doc state, throws various exceptions.
        archived_service.delete_action(lookup={'guid': {'$in': guids}})
        archived_service.command_delete(lookup={'guid': {'$in': guids}})

    def single_delete(self, guid):
        archived_service = superdesk.get_resource_service('archived')
        # checks doc state, throws various exceptions.
        archived_service.delete_action(lookup={'guid': guid})
        archived_service.command_delete(lookup={'guid': guid})

    def run(self, guids=[], file=None):
        if len(guids) != 0:
            self.bulk_delete(guids)

        if file:
            with open(file, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line.strip())
                    else:
                        continue

                    self.single_delete(data['guid'])


superdesk.command('app:deletedoc', DeleteDocCommand())
