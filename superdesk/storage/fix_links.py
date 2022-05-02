import copy
import superdesk

from flask import current_app as app
from superdesk.editor_utils import generate_fields, get_field_content_state


class MediaFixLinksCommand(superdesk.Command):
    """Fix media links in content.

    When moving an instance to different domain the links to media items
    can be broken if using Superdesk media storage. This command can check
    the links and fix them when appropriate.

    Usage::

        $ python manage.py media:fix_links --prefix "http://example.com/upload"

    Use the prefix to define the old url which should be fixed, links starting
    with other urls won't be updated.

    Options:

    -p, --prefix    URL prefix to fix. It will only fix links starting with it.
    -r, --resource  Only update specified resource.
    -d, --dry-run   Don't update just print item ids which would be updated.

    """

    option_list = [
        superdesk.Option("--prefix", "-p", dest="prefix", required=True),
        superdesk.Option("--resource", "-r", dest="resource", default=None),
        superdesk.Option("--dry-run", "-d", dest="dry_run", default=False, action="store_true"),
    ]

    resources = [
        "archive",
        "published",
        "items",
    ]

    def run(self, prefix, resource, dry_run):
        print("Fixing hrefs for prefix", prefix)
        for res in self.resources:
            updated = 0
            if resource and res != resource:
                continue
            print("Updating resource", res)
            service = superdesk.get_resource_service(res)
            for item in service.get_all():
                orig = copy.deepcopy(item)
                hrefs = {}
                updates = self.get_updates(item, prefix, hrefs)
                if updates:
                    updated += 1
                    if dry_run:
                        print("update", item["_id"], updates.keys())
                    else:
                        print(".", end="")
                        service.system_update(item["_id"], updates, orig)
            if not dry_run:
                print("")
            print("Done. Updated", updated, "items.")

    def get_updates(self, item, prefix, hrefs):
        updates = {}

        # check renditions
        renditions = item.get("renditions") or {}
        for rendition in renditions.values():
            if rendition and rendition.get("href") and rendition["href"].startswith(prefix):
                media = rendition.get("media")
                if not media:
                    print("Can't fix rendition", rendition)
                    continue
                _href = rendition["href"]
                if _href not in hrefs:
                    hrefs[_href] = app.media.url_for_media(media, rendition.get("mimetype"))
                rendition["href"] = hrefs[_href]
                updates["renditions"] = renditions

        # check associations - recursive
        associations = item.get("associations") or {}
        for assoc in associations.values():
            if assoc:
                assoc_updates = self.get_updates(assoc, prefix, hrefs)
                if assoc_updates:
                    updates["associations"] = associations

        # check editor fields - recursive
        fields_meta = item.get("fields_meta") or {}
        for field in fields_meta.keys():
            content_state = get_field_content_state(item, field) or {}
            entity_map = content_state.get("entityMap") or {}
            for entity in entity_map.values():
                if entity.get("type") == "MEDIA" and entity.get("data") and entity["data"].get("media"):
                    entity_updates = self.get_updates(entity["data"]["media"], prefix, hrefs)
                    if entity_updates:
                        generate_fields(item, [field], force=True)
                        updates["fields_meta"] = fields_meta
                        if item.get(field):
                            updates[field] = item[field]

        body_html = item.get("body_html")
        if item.get("body_html") and hrefs:
            for old_url, new_url in hrefs.items():
                item["body_html"] = item["body_html"].replace(old_url, new_url)
            if body_html != item["body_html"]:
                updates["body_html"] = item["body_html"]

        return updates


superdesk.command("media:fix_links", MediaFixLinksCommand())
