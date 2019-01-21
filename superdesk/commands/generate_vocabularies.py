# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from os.path import expanduser, abspath, exists

import json


class GenerateVocabularies(superdesk.Command):
    """Generate vocabularies.json from flat file

    This command generate the vocabularies.json file from a flat text file having the following structure:
    ::

        Vocabulary Label:
            item 1
            item 2
            item 3

    Vocabulary label must end by a colon (:). Indendation is not significant.
    By default vocabularies maps to an id with the label in lower case where spaces
    have been replaced by underscode (_).
    It is possible though to map to an other label/id. For this, you can specify a json
    file using the ``--key-map`` option. It expects a path to json file mapping from vocabulary label
    set in the flat text file to superdesk id (which will also be used as label).
    e.g.:

    .. code:: json

        {
            "author types": "author roles",
            "news statuses": null,
            "news urgencies": "urgency",
            "genres": {
                "name": "Genre",
                "extra": {"selection_type": "multi selection"},
            },
            "": {
                "extra": {"type": "unmanageable"}
            }
        }

    - plain text name will be used as label/id.
    - null means that the value must be ignored
    - a dict helps to manage more complicated mapping. See below for the keys which can be used.
    - empty string ("") can be used as key when extra must be applied to all non ignored vocabularies

    Key which can be used in dictionary:

    =====  ===========
    key    explanation
    =====  ===========
    name   used as label and _id (in lower case and with spaces replaced by underscodes)
    extra  a dictionary which will be merged to default one. Useful to add missing keys/values.
    =====  ===========

    You can also specify a path to a file containing a json array using ``--base`` which will contain
    the base vocabularies to use. If not specified, an empty array will be used.

    The generated json will be written to ``vocabularies.json`` in the current directory.
    """

    option_list = [
        superdesk.Option('-k', '--keys-map', help='key mapping json file'),
        superdesk.Option('-b', '--base', help='json array to use as base vocabularies'),
        superdesk.Option('-f', '--force', action="store_true",
                         help='overwritte "vocabularies.json" if it already exists'),
        superdesk.Option('source_file', help='plain text file with the vocabularies to create')
    ]

    def get_path(self, path):
        return abspath(expanduser(path))

    def run(self, keys_map, base, force, source_file):
        if exists("vocabularies.json"):
            if force:
                print('Overwriting "vocabularies.json" as requested')
            else:
                raise SystemExit('"vocabularies.json" file already exists, won\'t overwrite')
        if base is None:
            voc = []
        else:
            voc = json.load(open(self.get_path(base)))
            if not isinstance(voc, list):
                raise SystemExit('base vocabularies must be an array')

        if keys_map is None:
            keys_map = {}
        else:
            keys_map = {k.lower(): v for k, v in json.load(open(self.get_path(keys_map))).items()}

        base_extra = keys_map.pop("", {}).get("extra")

        with open(self.get_path(source_file)) as f:
            lines = f.readlines()

        skip = False
        current_voc = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.endswith(':'):
                skip = False
                name = line[:-1].strip()
                extra = None
                if name.lower() in keys_map:
                    name = keys_map[name.lower()]
                    if name is None:
                        skip = True
                        continue
                    if isinstance(name, dict):
                        extra = name.get(u'extra')
                        name = name.get(u'name')
                current_voc = {
                    '_id': name.lower().replace(' ', '_'),
                    "display_name": name,
                    "type": "manageable",
                    "unique_field": "qcode",
                    "service": {"all": 1},
                    'items': [],
                }
                if base_extra:
                    current_voc.update(base_extra)
                if extra:
                    current_voc.update(extra)
                voc.append(current_voc)
            elif not skip:
                if current_voc is None:
                    raise SystemExit(
                        'Invalid source file! Your file must start with a vocabularies label (it must end with a '
                        'colon)')
                item = {
                    u'name': line,
                    u'qcode': line,
                    u'is_active': True,
                }
                current_voc['items'].append(item)

        json.dump(voc, open("vocabularies.json", "w"), indent=4)
        print('Data generated in "vocabularies.json"')


superdesk.command('vocabularies:generate', GenerateVocabularies())
