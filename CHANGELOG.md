# Superdesk Server Changelog

## [Unreleased]

### Added

- Add `USE_TAKES` (default: `True`) config to be able to turn off takes packages.

## [1.1] 2016-08-29

### Added

- Add destination picker for unspike action.
- Highlight matching terms in search results.

### Fixed

- Add missing associations data to HTTP PUSH publishing.
- Fix select area of interest func for embedded pictures.
- Fix uploading/editing of dictionaries.
- Filter out inactive search providers.
- Fix error when setting default value for cv field.
- Fix publishing of stories with feature image.
- Fix `LDAP_SERVER_PORT` setting not being integer.
- Fix duplicate subject codes parsing for nitf.
- Strip markup while matching content filters
- Make newly created items invisible, show it only after saving.


## [1.0] 2016-08-17

### Fixed

- Fix the handling of `anpa_take_key` for null values.

## [1.0-beta1] 2016-04-25

- initial release
