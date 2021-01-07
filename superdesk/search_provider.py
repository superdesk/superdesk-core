class SearchProvider:
    """Base class for Search Providers.

    You can use ``self.provider`` to get config data.
    """

    #: Provider Type Label
    label = "unknown"

    def __init__(self, provider):
        """Create search provider instance.

        :param provider: provider data dict
        """
        self.provider = provider

    def find(self, query):
        """Find items using query.

        This must return cursor like object.

        :param query: query dict
        """
        raise NotImplementedError

    def fetch(self, guid):
        """Get single item.

        Get an item before archiving it. Should contain all metadata.

        :param guid: item guid
        """
        raise NotImplementedError

    def fetch_file(self, href):
        """Fetch binary using given href.

        Href is from renditions dict.

        :param href: binary href
        """
        raise NotImplementedError
