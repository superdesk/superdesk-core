# Superdesk Server Changelog

## [1.10.3] 2018-01-25 

### Fixed

- Fix the genre translation.

## [1.10.2] 2018-01-23

### Fixed

- Fix the sync vocabulary command.

## [1.10.1] 2018-01-19

### Added

- Add sync vocabulary item names/translations command.

## [1.10] 2018-01-05

### Fixed

- Fix NITF Formatter - remove `<styule>` element.
- Fix RSS ingest for feeds with missing guid field.

### Added

- Add feedback url to client config.

## [1.9] 2017-12-14

### Fixed

- Reset description when abstract is empty in NINJS format.
- Fix update of editor state, extra fields and associations on rewrite.
- Avoid overwriting assocations data if there was no update on the associated item.
- Fix the update of image metadata on correction.
- Set Flask version to match Eve.
- Fix `MEDIA_PREFIX` setting for Content API.
- Fix Superdesk NINJS Schema.
- Refactor purging of audit collection.
- Reorder fields on default content profile.
- Fix parsers for AP and DPA.
- Validate SMS message when SMS is enabled.
- Fix image upload for images requiring a rotation.
- Abort sending items to readonly stage.

### Added

- Add annotations field to item schema.
- Add support for vocabulary items translations.
- Add `firstpublished` field to NINJS format.
- Add Slack channel name to desks and Slack user name to users.
- Add setting for basic content type schema and editor.
- Add annotations types vocabulary.
- Add custom embed field support.
- Add custom media field support.
- Add mongo index to `archive_history` and `legal_archive_history`.
- Add support for extra fields in filter conditions.
- Add support for extra fields in content profile.
- Add support for signatures to HTTP Push output.
- Add Authors to NINJS format.
- Add Job title vocabulary.
- Add time to read into NINJS.
- Add Contacts resource.
- Add Author roles vocabulary.
- Add setting for Publish Queue expiry.
- Add NINJS parser for ingesting of text with featuremedia.
- Add helper text for custom fields.
- Add author flag to users.
- Add attachments resource with NINJS output support.
- Allow extra fields in item schema.
- Add desktop notifications to user preferences.
- Add publisher Livesite Editor privilege.
- Enable events publishing.
- Add support for language in content profile.
- Add SAML Auth method.
- Allow creation of new Vocabularies.
- Added reading time to ninjs output (`readtime` property)
- Added authors to ninjs output (`authors` property)

### Changed

- Make websocket exchange name configurable.
- Simplify email validation.
- Make user sign-off field nullable.
- Remove `SERVER_NAME` and `URL_PROTOCOL` settings.
- Upgrade LDAP package.
- Add file extension to urls for local media storage.
- Enable DELETE for vocabularies.
- Moved non etree releated methods from `etree` module to the new `text_utils` one
- Improved error handling in FTP ingest.
- Takes are removed from core.

## [1.8.6] 2017-10-11

### Fixed

- Fix parsing of ANSA NewsmlG2 feed.
- Add nijs parser to ingest both text and feature media.
- Fix issue where user cannot publish after removing feature media.

## [1.6.3] 2017-09-25

### Fixed

- Fix user email validation to allow subdomains.

## [1.8.5] 2017-08-02

### Fixed

- Fix unique validator when search backend is configured.
- Fix AP and DPA parsers.
- Validate the SMS message when SMS is enabled.
- Source is preserved when the story is rewritten

### Changed

- Make displaying crops for featured media config option.

## [1.8.4] 2017-06-30

### Fixed

- Fix bad field type in Wordpress import.
- Fix fetching media from relative URLs.
- Remove SMS flag on duplication.
- Fix item history for scheduled items.
- Ingested content should preserve its source on duplication/rewrite.

## [1.8.3] 2017-06-19

### Fixed

- Fix wordpress parser image embeds.

## [1.8.2] 2017-06-16

### Fixed

- Fix wordpress parser image handling.

## [1.8.1] 2017-06-16

### Fixed

- Fix wordpress import - upload image to archive and generate renditions.
- Fix publish when feature media or media description is required

## [1.8] 2017-06-09

### Fixed

- Remove `pf:` from content filter messages.
- Handle deleted/disabled content profiles.
- Fix clean images command not working with 1000+ images on S3.
- Fix mapping for content api items to match superdesk resources.
- Fix `iunieuq` filter when `search_backend` is configured on resource.
- Make legal archive optional.
- Set celery timezone to UTC.
- Change default settings to not contain AAP info.

### Added

- Expose expiry settings via Superdesk API.
- Add `CELERY_WORKER_CONCURRENCY` setting.
- Add `client_config` resource for exposing some config to client.
- Add option to move ingested files via FTP to another path.
- Support `keywords` field in content profile editor.
- Let vocabularies specify schema.
- Implement google oauth2 authentication.
- Internal resource for content api items.
- Add full elastic reindex from mongodb.
- Test ingest config when creating/updating provider.
- Add option for relative media urls.
- Add Wordpress WXR parser.
- Allow filtering of associated items by products.
- Add `source` field to NINJS output.
- Add extract html macro from NTB.
- Create new template when new content profile is created.

### Changed

- Remove mark desk flag when item is duplicated.
- Prevent changes to items on readonly stage.
- Create mongo indexes and elastic mapping only during `app:initialize_data` action.

## [1.7.1] 2017-06-05

### Fixed

- Add `_etag` to `item:lock` and `item:unlock` notifications.
- Fix NITF formatter inserting too many line breaks.

## [1.7] 2017-05-23

### Fixed

- Keep item schedule when using internal destinations.
- Set pending state on items when there is an error during enqueue in order to try again next time.
- Fix unlock requiring privileges to modify unique name.
- Update mapping for associations to enable searching for featuremedia.
- Fix ap anpa parser throwing exception in dateline parsing.
- Update embedded image caption using associations metadata.
- Fix pydocstyle version.
- Fix renditions generator when crop is missing.
- Fix rewrites missing `_current_version` field.
- Fix `first_paragraph` template filter.
- Avoid dynamic elastic mapping.
- Fix image renditions being few pixels shorter than specified width.
- Add mongo index on `guid` for `archive_versions` resource.
- Remove highlights info and marked for desk status from archived items.
- Optimize content filtering for global block filters.
- Content filter referenced by api product sould not be deletable.
- Non required fields in content profile should have minlenght set to `0`.
- Fix update ingest when scheme is missing.
- Fix Correct and Kill buttons missing when workqueue item is opened.
- Handle newlines in kill template body.
- Fix resending of published item to digital subscribers.
- Update session `_updated` time on autosave.
- Use item `_id` when adding to highlights instead of `guid`.
- Fix history for highlights.
- Validate updated content when checking marked not for publication.
- Fix search results highlighting with elastic 2.x.
- Previous versions of killed item should not be visible in Content API.
- Use self-closed html elements for empty fields in NewsMLG2 formatter.
- Fix handling of existing digital package if takes are disabled.
- Apply specified stage when getting items from external source.
- Remove obsolete Public API auth module.
- Avoid elastic index initialization in rest/work processes.
- Handle `<br />` in NITF formatter.
- Remove fields excluded from profile in output.
- Fix missing html part in email output when dateline was missing.
- Preserve `\r` char when parsing content.
- Fix validate exception catching in validate service.
- Use `superdesk.macros` as a default value for `MACROS_MODULE` config.
- Ingest supports items with predefined ids.

### Added

- Push notification when subscriber is added/updated.
- Push notification when scheduled item gets published.
- Purge content from Content API when expired.
- Purge exported files from storage.
- Add filter condition for *embargo* field.
- Allow search provider to specify label.
- Add `fix_html_void_elements` to `superdesk.etree` and use it in NewsMLG2 formatter.
- Provide distinct caption and description for images.
- Allow duplication to different desk/stage.
- Add product types to products.
- Add internal destinations feature.
- Allow ingest triggering via webhook.
- Add item versioning to Content API.
- Add Wufoo service provider and parser.
- Keep audit of items/assets retrieved from Content API.
- Add export feature for items.
- Add support for elastic 2.x.
- Display instance registration form on first login.

### Changed

- Start using signature version 4 on S3.
- When unlocking an item save existing autosave as a new item version.
- Remove groups.
- Don't put default ednote for embargoed stories.
- Stop generating custom crops on upload, only create system renditions.
- Use headline for kill email subject.
- Remove Reuters provider from init data.
- Update NINJS superdesk output.
- Update dependencies (eve, hachoir3, pillow, arrow).
- Change `search_providers_proxy` privilege to `archive`.
- Separate history from item versions.
- Move analytics into its own repository.
- Switch from `ElementTree` and `BeautifulSoup` to `lxml` library.

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
