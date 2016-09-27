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
from eve.utils import ParsedRequest


DEFAULT_DATA_UPDATE_DIR_NAME = 'data_updates'
MAIN_DATA_UPDATES_DIR = os.path.abspath(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), os.pardir, DEFAULT_DATA_UPDATE_DIR_NAME))
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


def get_dirs(only_relative_folder=False):
    dirs = []
    try:
        with superdesk.app.app_context():
            dirs.append(current_app.config.get('DATA_UPDATES_PATH', DEFAULT_DATA_UPDATE_DIR_NAME))
    except RuntimeError:
        # working outside of application context
        pass
    if not only_relative_folder:
        dirs.append(MAIN_DATA_UPDATES_DIR)
    assert len(dirs) <= 2
    return dirs


def get_data_updates_files(strip_file_extension=False):
    """Return the list of data updates filenames.

    .py extension can be removed with `strip_file_extension` parameter.
    """
    files = []
    # create folder if doens't exist
    for folder in get_dirs():
        if not os.path.exists(folder):
            continue
        # list all files from data updates directory
        if os.path.exists(folder):
            files += [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    # keep only data updates (00000x*.py)
    files = [f for f in files if DATA_UPDATES_FILENAME_REGEX.match(f)]
    # order file names
    files = sorted(files)
    # remove .py extention if needed
    if strip_file_extension:
        files = [f.rstrip('.py') for f in files]
    return files


class DataUpdateCommand(superdesk.Command):
    """Parent class for Upgrade and Downgrade commands.

    It defines options and initialize some variables in `run` method.
    """

    option_list = [
        superdesk.Option('--id', '-i', dest='data_update_id', required=False,
                         choices=get_data_updates_files(strip_file_extension=True),
                         help='Data update id to run last'),
        superdesk.Option('--fake-init', dest='fake', required=False, action='store_true',
                         help='Mark data updates as run without actually running them'),
        superdesk.Option('--dry-run', dest='dry', required=False, action='store_true',
                         help='Does not mark data updates as done. This can be useful for development.'),
    ]

    def get_applied_updates(self):
        req = ParsedRequest()
        req.sort = '-name'
        return tuple(self.data_updates_service.get(req=req, lookup={}))

    def run(self, data_update_id=None, fake=False, dry=False):
        self.data_updates_service = superdesk.get_resource_service('data_updates')
        self.data_updates_files = get_data_updates_files(strip_file_extension=True)
        # retrieve existing data updates in database
        data_updates_applied = self.get_applied_updates()
        self.last_data_update = data_updates_applied and data_updates_applied[-1] or None
        if self.last_data_update:
            if self.last_data_update['name'] not in self.data_updates_files:
                print('A data update previously applied to this database (%s) can\'t be found in %s' % (
                      self.last_data_update['name'], ', '.join(get_dirs())))

    def compile_update_in_module(self, data_update_name):
        date_update_script_file = None
        for folder in get_dirs():
            date_update_script_file = os.path.join(folder, '%s.py' % (data_update_name))
            if os.path.exists(date_update_script_file):
                break
        assert date_update_script_file is not None, 'File %s has not been found' % (data_update_name)
        # create a module instance to use as scope for our data update
        module = ModuleType('data_update_module')
        with open(date_update_script_file) as f:
            # compile data update script file
            script = compile(f.read(), date_update_script_file, 'exec')
            # excecute the script in the module
            exec(script, module.__dict__)
        return module

    def in_db(self, update):
        return update in map(lambda _: _['name'], self.get_applied_updates())


class Upgrade(DataUpdateCommand):
    """Runs all the new data updates available.

    If `data_update_id` is given, runs new data updates until the given one.
    """

    def run(self, data_update_id=None, fake=False, dry=False):
        super().run(data_update_id, fake, dry)
        data_updates_files = self.data_updates_files
        # drops updates that already have been applied
        data_updates_files = [update for update in data_updates_files if not self.in_db(update)]
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
            if not dry:
                # store the applied data update in the database
                self.data_updates_service.create([{'name': data_update_name}])
        if not data_updates_files:
            print('No data update to apply.')


class Downgrade(DataUpdateCommand):
    """Runs the latest data update backward.

    If `data_update_id` is given, runs all the data updates backward until the given one.
    """

    def run(self, data_update_id=None, fake=False, dry=False):
        super().run(data_update_id, fake, dry)
        data_updates_files = self.data_updates_files
        # check if there is something to downgrade
        if not self.last_data_update:
            print('No data update has been already applied')
            return False
        # drops updates which have not been already made (this is rollback mode)
        data_updates_files = [update for update in data_updates_files if self.in_db(update)]

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
            if not dry:
                # remove the applied data update from the database
                self.data_updates_service.delete({'name': data_update_name})
        if not data_updates_files:
            print('No data update to apply.')


class GenerateUpdate(superdesk.Command):
    """Generate a file where to define a new data update."""

    option_list = [
        superdesk.Option('--resource', '-r', dest='resource_name', required=True,
                         help='Resource to update'),
        superdesk.Option('--global', '-g', dest='global_update', required=False, action='store_true',
                         help='This data update belongs to superdesk core'),
    ]

    def run(self, resource_name, global_update=False):
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        # create a data update file
        try:
            last_file = get_data_updates_files()[-1]
            name_id = int(last_file.replace('.py', '').split('_')[0]) + 1
        except IndexError:
            name_id = 0
        if global_update:
            update_dir = MAIN_DATA_UPDATES_DIR
        else:
            update_dir = get_dirs(only_relative_folder=True)[0]
        if not os.path.exists(update_dir):
            os.makedirs(update_dir)
        data_update_filename = os.path.join(update_dir, '{:05d}_{}_{}.py'.format(name_id, timestamp, resource_name))
        if os.path.exists(data_update_filename):
            raise Exception('The file "%s" already exists' % (data_update_filename))
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
