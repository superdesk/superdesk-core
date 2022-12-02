from superdesk.metadata.utils import _set_highlight_query
from werkzeug.datastructures import ImmutableMultiDict
import json


class HighlightsSearchMixin:
    def _get_highlight_query(self, req):
        """Get and set highlight query

        :param req parsed request
        """
        args = getattr(req, "args", {})
        source = json.loads(args.get("source")) if args.get("source") else {"query": {"filtered": {}}}
        if source:
            _set_highlight_query(source)

            # update req args
            try:
                req.args = req.args.to_dict()
            except AttributeError:
                pass
            req.args["source"] = json.dumps(source)
            req.args = ImmutableMultiDict(req.args)

        return req

    def _get_highlight(self, req, lookup):
        if req is not None:
            req = self._get_highlight_query(req)

        if req is None and lookup is not None and "$or" in lookup:
            # embedded resource generates mongo query which doesn't work with elastic
            # so it needs to be fixed here
            return req, lookup["$or"][0]

        return req, lookup
