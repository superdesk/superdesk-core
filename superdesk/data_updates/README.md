# Keep the database up to date with Data Updates

1. [What Data Updates are made for](#what-data-updates-are-made-for)  
1. [Create a Data Update](#create-a-data-update)  
1. [Apply a Data Update](#apply-a-data-update)

## What Data Updates are made for

During the application development, it can happen that a developer needs to change something in the current data.
Data Updates are made to share this change between developers and instances.
There are many occasions to create a Data Update:

- reflect a change in the data schema to the current data
- add a default value for a new field
- set an index on a field
- and a lot more...

## Create a Data Update

### 1. Create the Data Update file

```
usage: manage.py data:generate_update [-?] --resource RESOURCE_NAME [--global]

Generate a file where to define a new data update

optional arguments:
  -?, --help      show this help message and exit
  --resource RESOURCE_NAME, -r RESOURCE_NAME Resource to update
  --global, -g      This data update belongs to superdesk core

```

use `--global` if you want to create this file in `superdesk-core` repository. Otherwise it will be added to the current `superdesk` project.

Example:
```
./manage.py data:generate_update -r vocabularies
Data update file created data_updates/00001_20160616-115845_vocabularies.py
```

### 2. Implement the Data Update

Open the previously created file, and start to implement the `forwards` and `backwards` methods.

1. `forwards`: apply the wanted changes in the database
1. `backwards`: revert the changes in the database.


```python
class DataUpdate(BaseDataUpdate):

  resource = 'vocabularies'

  def forwards(self, mongodb_collection, mongodb_database):
    raise NotImplementedError()

  def backwards(self, mongodb_collection, mongodb_database):
    raise NotImplementedError()
```


## Apply a Data Update

```
usage: manage.py data:upgrade [-?]
                              [--id {name of the data update}]
                              [--fake-init] [--dry-run]

Runs all the new data updates available. If `data_update_id` is given, runs
new data updates until the given one.

optional arguments:
  -?, --help     show this help message and exit
  --id {}        Data update id to run last
  --fake-init    Mark data updates as run without actually running them
  --dry-run      Does not mark data updates as done. This can be
                 useful for development.
```

### Use cases:

- After a fresh install, when the data base is still empty, you don't need the existing data update. So you may want to mark them as run.  
`manage.py data:upgrade --fake-init`

- To apply all available data updates, run  
`manage.py data:upgrade`  
You can specify with `--id` a data update where to stop

- To rollback the last made data updates, run  
`manage.py data:downgrade`  
You can specify with `--id` a data update where to go

- You are developing a Data Update and you want to run it without marking it as run. So run your script with  
`manage.py data:upgrade --dry-run`  
