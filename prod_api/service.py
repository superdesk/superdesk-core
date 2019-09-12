import superdesk
from flask import current_app as app


class ProdApiService(superdesk.Service):
    """
    Base service for production api services
    """

    excluded_fields = {
        '_etag',
        '_type',
        '_updated',
        '_created',
        '_current_version',
        '_links',
    }

    def on_fetched(self, result):
        """
        Event handler when a collection of items is retrieved from database.
        Post-process a fetched items.
        :param dict result: dictionary contaning the list of fetched items and
         some metadata, e.g. pagination info.
        """
        for doc in result['_items']:
            self._process_fetched_object(doc)

    def on_fetched_item(self, doc):
        """
        Event handler when a single item is retrieved from a database.
        Post-process a fetched item.
        :param dict docs: fetched items from a database.
        """
        self._process_fetched_object(doc)

    def _process_fetched_object(self, doc):
        """
        Does some processing on the document fetched from database.
        :param dict document: MongoDB document to process
        """
        # remove keys from a response
        for key in self.excluded_fields:
            doc.pop(key, None)

        # post process renditions
        self._process_item_renditions(doc)

    def _process_item_renditions(self, item):
        hrefs = {}
        if item.get('renditions'):
            for _k, v in item['renditions'].items():
                if 'media' in v:
                    href = v.get('href')
                    media = v.pop('media')
                    v['href'] = app.media.url_for_media(media, v.get('mimetype'))
                    hrefs[href] = v['href']
        return hrefs
