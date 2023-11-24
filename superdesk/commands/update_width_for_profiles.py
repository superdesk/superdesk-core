import superdesk
import bson


class UpdateWidthForProfiles(superdesk.Command):
    """
    Update width for fields in content profiles
    Example:
    ::

        $ manage.py app:updateWidthForProfiles

    """

    def run(self):
        """
        Run the command to update width for fields in content profiles.
        """
        content_profiles_service = superdesk.get_resource_service("content_types")
        for profile in content_profiles_service.get(req=None, lookup=None):
            try:
                editor = profile.get("editor", {})
                for field, properties in editor.items():
                    if properties and "sdWidth" not in properties:
                        properties["sdWidth"] = "full"
                content_profiles_service.system_update(bson.ObjectId(profile["_id"]), {"editor": editor}, profile)
                print(f"Content Profile {profile['_id']} updated successfully")
            except Exception as e:
                print(f"Error updating Content Profile {profile['_id']}: {str(e)}")


superdesk.command("app:updateWidthForProfiles", UpdateWidthForProfiles())
