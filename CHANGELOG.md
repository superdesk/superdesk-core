# Superdesk Server Changelog

## [1.6.2] 2017-03-01

### Fixed

- Fix city names in locators vocabulary.
- Fix again *Fix email formatter to preserve line breaks in text version.*.

## [1.6.1] 2017-02-28

### Fixed

- Fix email formatter to preserve line breaks in text version.
- Make archived items published from invisible stages visible.

## [1.6.0] 2017-02-16

### Fixed

- Report original exception details to sentry.
- Ensure username is unique.
- Remove the link to other stories.
- Keep renditions until item expiry.
- Fix renditions if published it can't be removed.
- Activate token should be active for 7 days.
- Fix bad argument handling in data upgrades.
- Fix image cropping if mimetype is missing for some rendition.
- Fix `place` filter condition.
- Reset `event_id` for unlinked stories.
- Fix resending of stories when `NO_TAKES` is on.
- Fix image cropping for renditions defined via vocabulary.
- Fix dateline is required for picture item kill.
- Fix push to send all renditions of package items and embedded items.
- Fix reuters content formatting.
- Fix `item:expired` notification to send item id.
- Fix rss guid handling when it's not permalink.
- Fix email subject with utf8.
- Stop retrying enqueue on error.
- Make word counts consistent with UI.

### Added

- Add mark stories for desks.
- Add endpoint to generate content api tokens for subscribers.
- Activity reports generating and management.
- Add audit collection gc.
- Add EFE specific parser.
- Password-less authentication via xmpp.
- Document authentication.
- New operators for filter conditions.
- Store ingested data that could not be parsed.
- Add `CELERY_PREFIX` config option.
- Add `evolvedfrom` to ninjs output.
- Copy metadata field from parent to associated items.
- Add archived collection curation functions.
- Add group label to macros.
- Add filter to block api content.

### Changed

- Refactor ingest providers registry.
- Refactor search providers registry.
- Add associations to rewrites and takes.
- Update celery to 4.0.
- Make single-line view a user preference.

## [1.5.2] 2017-01-18

### Fixed

- Update sign off if mapped field is updated on user.
- Fix editing content profiles with custom fields.
- Fix publishing with content profiles.

### Added

- Implement email publishing to multiple users via bcc.

## [1.5.1] 2017-01-03

### Changed

- Bypass content validation using profile for auto published content.

### Fixed

- Clean up old item locks.
- Mark search provider as used when an item is fetched.
- Fix issues with dateline validation for content profile.

## [1.5] 2016-12-21

### Fixed

- Push notification when dictionary is created/updated.
- Fix `backend_meta` service on python3.4.
- Parse byline from rss.
- Fix slow query in duplicate item.
- In app factory load `CORE_APPS` before `INSTALLED_APPS`.
- Clear SMS flag for new takes and updates.
- Load init files from core if missing in data folder.
- Fix xml file ingest with BOM or non-unicode encoding.

### Changed

- Set default content expiry to `0`.
- Use `CONTENTAPI_URL` setting for content API.
- Use projections in search results.
- App init command won't override modified data. Use `-f` to keep old behaviour.
- Make `byline` empty on kill.
- Remove `By` prefix from `byline` in nitf output.
- Initial [Content API Refactoring](http://superdesk.readthedocs.io/en/latest/contentapi.html).

### Added

- Allow duplication of items in text archive.
- Add `Place` to criteria fields for content filters.
- Add `PUBLISHED_CONTENT_EXPIRY_MINUTES` for published items.
- Add `firtscreated` field to superdesk ninjs output.
- Add `desk:preferred` user preference.
- Add `suggestions` resource for related items suggestion.

## [1.4.7] 2016-12-20

### Fixed

- Fix comments notifications for users with `.` in username.

## [1.4.6] 2016-12-14

### Fixed

- Fix parsing of non-unicode nitf.
- Fix ingestion with refresh rate < 1m.

## [1.4.5] 2016-12-07

### Added

- Add option to skip iptc codes processing on ingest.

## [1.4.4] 2016-12-05

### Fixed

- Use default language if no language is set on desk.

## [1.4.3] 2016-11-30

### Fixed

- Allow tables in NITF output.

## [1.4.2] 2016-11-29

### Added

- Add support for desk language

### Fixed

- Fix validation in case of error in list field

## [1.4.1] 2016-11-22

### Fixed

- Fix missing validation error for embedded items.

## [1.4] 2016-11-15

### Added

- Add option to generate short item ids.
- Add support for translate item action.

### Fixed

- Set celery version <4.
- Allow email formatter for publishing.
- Improve word counting.
- Ignore dateline when validating correction.
- Fix online users info when doing sessions gc.
- Fix rss ingest when missing last updated date.
- Prevent rss ingested items to have timestamps in future.

## [1.3] 2016-10-14

### Added

- Add `superdesk.cache` module.
- Add htm2nitf method to NITF formatter
- Add basic curation function for text archive
- Add embargo privilege

### Fixed

- PA NITF ingest fixes
- Set ingest default values only of not set via profile
- Fix image cropping after updating image crop size vocabulary
- Preserve language on update/rewrite actions
- Update word count on save and publish action
- Allow duplicating items to different desks
- Update `versioncreated` of duplicated item

## [1.2] 2016-10-04

### Added

- Add spike expiry config setting
- Implement removing of content profiles
- Add `NO_TAKES` (default: `False`) config to be able to turn off takes packages.

### Fixed

- Fix scheduled items should not block publishing of normal items.
- Fix the query for genre in content filters
- Fix upload after changes to crop sizes vocabulary
- Fix saved search endpoint to return proper hateoas links
- Fix deleting of routed ingest items
- Use timezone for highlights queries
- Fix publishing of package items when those should be just included
- Fix only showing 25 desks
- Fixes for NITF formatter
- Fix fetching of media items - should not use content profiles
- Fix associated items validation - refresh before validation
- Fix query to return items for generating highlights

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
