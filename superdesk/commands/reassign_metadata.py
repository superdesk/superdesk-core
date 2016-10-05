import sys
import superdesk


class ReassignMetadataCommand(superdesk.Command):
    """
    Update metadata for a document in both Mongodb and ElasticSearch by supplying a GUID

    manage.py app:update:metadata
        -i urn:newsml:localhost:2016-09-12T12:11:40.160498:7237e59f-c42d-4865-aee5-e364aeb2966a
        -m anpa_category
        -v x

    -m source -v AAP (value is a string name value)
    -m anpa_category -v x (value is a qcode from vocabularies.json id=categories)
    """

    option_list = [
        superdesk.Option('--guid', '-i', dest='guids', required=True, action='append',
                         help='pass guids of articles to update a metadata item'),
        superdesk.Option('--meta', '-m', dest='key', required=True),
        superdesk.Option('--value', '-v', dest='value', required=True)
    ]

    def run(self, guids, key, value):
        category_list = superdesk.get_resource_service('vocabularies').find_one(req=None, _id='categories')
        category_dict = {entry['qcode']: entry for entry in category_list['items']}
        patched = value

        if key not in ['anpa_category', 'source']:
            print('Invalid meta value to update.')
            sys.exit()

        if key == 'anpa_category' and value not in category_dict:
            print('Setting an invalid category metadata qcode.')
            sys.exit()

        if key == 'anpa_category':
            entry = category_dict[value]
            patched = [{
                'qcode': entry.get('qcode'),
                'name': entry.get('name'),
                'subject': entry.get('subject', None),
                'scheme': entry.get('scheme', None)
            }]

        service = superdesk.get_resource_service('archived')

        docs = service.find({'guid': {'$in': guids}})
        for original in docs:
            res = service.system_update(original['_id'], {key: patched}, original)
            print(res)


superdesk.command('app:update:metadata', ReassignMetadataCommand())
