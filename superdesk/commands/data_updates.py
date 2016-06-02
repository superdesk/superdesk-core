# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from string import Template
from types import ModuleType
from flask import current_app
import superdesk
import getpass
import os
import re
import time


DATA_UPDATES_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'data_updates'))
DATA_UPDATES_FILENAME_REGEX = re.compile('^(\d+).*\.py$')
DATA_UPDATE_TEMPLATE = '''
# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : $user
# Creation: $current_date

from superdesk.commands.data_updates import DataUpdate


class DataUpdate(DataUpdate):

    resource = '$resource'

    def forwards(self, mongodb_collection, mongodb_database):
        $default_fw_implementation

    def backwards(self, mongodb_collection, mongodb_database):
        $default_bw_implementation
'''.lstrip('\n')
DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = 'raise NotImplementedError()'
DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION = 'raise NotImplementedError()'


def get_data_updates_files(strip_file_extension=False):
    '''

    Returns the list of data updates filenames.
    .py extension can be removed with `strip_file_extension` parameter.

    '''
    # create folder if doens't exist
    if not os.path.exists(DATA_UPDATES_DIR):
        os.makedirs(DATA_UPDATES_DIR)
    # list all files from data updates directory
    files = [f for f in os.listdir(DATA_UPDATES_DIR) if os.path.isfile(os.path.join(DATA_UPDATES_DIR, f))]
    # keep only data updates (00000x*.py)
    files = [f for f in files if DATA_UPDATES_FILENAME_REGEX.match(f)]
    # order file names
    files = sorted(files)
    # remove .py extention if needed
    if strip_file_extension:
        files = [f.rstrip('.py') for f in files]
    return files


class DataUpdateCommand(superdesk.Command):
    '''

    Parent class for Upgrade and Downgrade commands.
    It defines options and initialize some variables in `run` method.

    '''
    option_list = [
        superdesk.Option('--id', '-i', dest='data_update_id', required=False,
                         choices=get_data_updates_files(strip_file_extension=True),
                         help='Data update id to run last'),
        superdesk.Option('--fake-init', dest='fake', required=False, action='store_true',
                         help='Mark data updates as run without actually running them'),
    ]

    def run(self, data_update_id=None, fake=False):
        self.data_updates_service = superdesk.get_resource_service('data_updates')
        self.data_updates_files = get_data_updates_files(strip_file_extension=True)
        # retrieve existing data updates in database
        self.data_updates_applied = tuple(self.data_updates_service.get(req=None, lookup={}))
        self.last_data_update = self.data_updates_applied and self.data_updates_applied[-1] or None
        if self.last_data_update:
            if self.last_data_update['name'] not in self.data_updates_files:
                print('A data update previously applied to this database (%s) can\'t be found in %s' % (
                      self.last_data_update['name'], DATA_UPDATES_DIR))

    def compile_update_in_module(self, data_update_name):
        date_update_script_file = os.path.join(DATA_UPDATES_DIR, '%s.py' % (data_update_name))
        # create a module instance to use as scope for our data update
        module = ModuleType('data_update_module')
        with open(date_update_script_file) as f:
            # compile data update script file
            script = compile(f.read(), date_update_script_file, 'exec')
            # excecute the script in the module
            exec(script, module.__dict__)
        return module


class Upgrade(DataUpdateCommand):
    '''

    Runs all the new data updates available.
    If `data_update_id` is given, runs new data updates until the given one.

    '''
    def run(self, data_update_id=None, fake=False):
        super().run(data_update_id, fake)
        data_updates_files = self.data_updates_files
        # drops updates that already have been applied
        if self.last_data_update:
            if self.last_data_update['name'] in data_updates_files:
                data_updates_files = data_updates_files[data_updates_files.index(self.last_data_update['name']) + 1:]
        # drop versions after given one
        if data_update_id:
            if data_update_id not in data_updates_files:
                print('Given data update id not found in available updates. It may have been already applied')
                return False
            data_updates_files = data_updates_files[:data_updates_files.index(data_update_id) + 1]
        # apply data updates
        for data_update_name in data_updates_files:
            print('data update %s running forward...' % (data_update_name))
            module_scope = self.compile_update_in_module(data_update_name)
            # run the data update forward
            if not fake:
                module_scope.DataUpdate().apply('forwards')
            # store the applied data update in the database
            self.data_updates_service.create([{'name': data_update_name}])
        if not data_updates_files:
            print('No data update to apply.')


class Downgrade(DataUpdateCommand):
    '''

    Runs the latest data update backward.
    If `data_update_id` is given, runs all the data updates backward until the given one.

    '''
    def run(self, data_update_id=None, fake=False):
        super().run(data_update_id, fake)
        data_updates_files = self.data_updates_files
        # check if there is something to downgrade
        if not self.last_data_update:
            print('No data update has been already applied')
            return False
        # drops updates which have been already made (this is rollback mode)
        data_updates_files = data_updates_files[:data_updates_files.index(self.last_data_update['name']) + 1]
        # if data_update_id is given, go until this update (drop previous updates)
        if data_update_id:
            if data_update_id not in data_updates_files:
                print('Update %s can\'t be find. It may have been already downgraded' % (data_update_id))
                return False
            data_updates_files = data_updates_files[data_updates_files.index(data_update_id):]
        # otherwise, just rollback one update
        else:
            print('No data update id has been provided. Dowgrading to previous version: %s'
                  % self.last_data_update['name'])
            data_updates_files = data_updates_files[len(data_updates_files) - 1:]
        # apply data updates, in the opposite direction
        for data_update_name in reversed(data_updates_files):
            print('data update %s running backward...' % (data_update_name))
            module_scope = self.compile_update_in_module(data_update_name)
            # run the data update backward
            if not fake:
                module_scope.DataUpdate().apply('backwards')
            # remove the applied data update from the database
            self.data_updates_service.delete({'name': data_update_name})
        if not data_updates_files:
            print('No data update to apply.')


class GenerateUpdate(superdesk.Command):
    '''

    Generate a file where to define a new data update

    '''
    option_list = [
        superdesk.Option('--resource', '-r', dest='resource_name', required=True,
                         help='Resource to update'),
    ]

    def run(self, resource_name):
        # initial id is 0
        last_id = 0
        files = get_data_updates_files()
        # retrieve last id from files
        if files:
            # TODO: check if new ID exists in DB
            last_id = int(DATA_UPDATES_FILENAME_REGEX.match(files[-1]).groups()[0])
        # create a data update file
        data_update_filename = os.path.join(DATA_UPDATES_DIR, '{0:05d}.py'.format(int(last_id + 1)))
        with open(data_update_filename, 'w+') as f:
            template_context = {
                'resource': resource_name,
                'current_date': time.strftime("%Y-%m-%d %H:%M"),
                'user': getpass.getuser(),
                'default_fw_implementation': DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION,
                'default_bw_implementation': DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION
            }
            f.write(Template(DATA_UPDATE_TEMPLATE).substitute(template_context))
            print('Data update file created %s' % (data_update_filename))


superdesk.command('data:generate_update', GenerateUpdate())
superdesk.command('data:upgrade', Upgrade())
superdesk.command('data:downgrade', Downgrade())


class DataUpdate:

    def apply(self, direction):
        assert(direction in ['forwards', 'backwards'])
        collection = current_app.data.get_mongo_collection(self.resource)
        db = current_app.data.driver.db
        getattr(self, direction)(collection, db)
