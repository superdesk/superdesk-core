# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
from uuid import uuid4

import superdesk
from werkzeug.datastructures import ImmutableMultiDict
from eve.utils import ParsedRequest
from superdesk.text_utils import get_text
from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError
from apps.auth import get_user


class ConceptItemsService(BaseService):
    """
    CRUD service for concept items
    """

    def get(self, req, lookup):
        if all([req, req.sort]):
            CASE_INSENSITIVE_COLLATION = '{"locale": "en", "strength":"1"}'
            COLLATION_SORT_ARGS = (
                "name",
                "-name",
                "definition_html",
                "-definition_html",
                "definition_text",
                "-definition_text",
            )

            # apply case insensitive collation only if collation was not provided explicitly
            # and sorting by `name`, `definition_html` or `definition_text` was used
            req_sort_args = [arg.strip() for arg in req.sort.split(",")]
            if [arg for arg in req_sort_args if arg in COLLATION_SORT_ARGS] and (
                not req.args or not req.args.get("collation")
            ):
                if req.args:
                    req.args = req.args.to_dict()
                    req.args["collation"] = CASE_INSENSITIVE_COLLATION
                    req.args = ImmutableMultiDict(req.args)
                else:
                    req.args = ImmutableMultiDict({"collation": CASE_INSENSITIVE_COLLATION})

            # if sort by (-)definition_html was used, we'll apply sort by definition_text under the hood
            if any([arg for arg in req_sort_args if arg in ("definition_html", "-definition_html")]):
                req_sort_args = ["definition_text" if arg == "definition_html" else arg for arg in req_sort_args]
                req_sort_args = ["-definition_text" if arg == "-definition_html" else arg for arg in req_sort_args]
                if req.args:
                    req.args = req.args.to_dict()
                    req.args["sort"] = ",".join(set(req_sort_args))
                    req.args = ImmutableMultiDict(req.args)
                else:
                    req.args = ImmutableMultiDict({"sort": ",".join(set(req_sort_args))})
                req.sort = req.args["sort"]

        return super().get(req, lookup)

    def on_create(self, docs):
        for doc in docs:
            self._validate_properties(doc)
            self._validate_language(doc)
            self._setup_created_by(doc)
            self._setup_group_id(doc)
            self._fill_definition_text(doc)

    def on_replace(self, doc, original):
        self._validate_properties(doc)
        self._validate_language(doc)
        self._validate_group_id(doc)
        self._setup_created_by(doc, original)
        self._setup_updated_by(doc)
        self._fill_definition_text(doc)

    def on_update(self, updates, original):
        if "cpnat_type" in updates:
            # we must validate `properties` even if they were not in payload
            if "properties" not in updates and "properties" in original:
                updates["properties"] = original["properties"]
        elif "properties" in updates:
            # we must validate `cpnat_type` even if it was not in payload
            updates["cpnat_type"] = original["cpnat_type"]
        if "cpnat_type" in updates:
            self._validate_properties(updates)

        if "language" in updates:
            self._validate_language(updates)

        if "definition_html" in updates:
            self._fill_definition_text(updates)

        self._setup_updated_by(updates)

    def _validate_language(self, doc):
        # fetch languages from CVs
        req = ParsedRequest()
        req.projection = json.dumps({"items.qcode": 1})

        try:
            languages = (
                superdesk.get_resource_service("vocabularies").find_one(req=req, _id="languages").get("items", [])
            )
        except AttributeError:
            raise SuperdeskApiError.badRequestError(
                message="Request is not valid",
                payload={"language": "Concept items requires 'languages' vocabulary to be set"},
            )

        languages_qcodes = [lang["qcode"] for lang in languages]

        if doc["language"] not in languages_qcodes:
            raise SuperdeskApiError.badRequestError(
                message="Request is not valid", payload={"language": "unallowed value '{}'".format(doc["language"])}
            )

    def _validate_group_id(self, doc):
        if "group_id" not in doc:
            raise SuperdeskApiError.badRequestError(
                message="Request is not valid", payload={"group_id": "This field is required"}
            )

    def _fill_definition_text(self, doc):
        doc["definition_text"] = get_text(doc["definition_html"], content="html", lf_on_block=True).strip()

    def _validate_properties(self, doc):
        getattr(self, "_validate_{}_properties".format(doc["cpnat_type"].rsplit(":", 1)[-1].lower()))(doc)

    def _validate_abstract_properties(self, doc):
        if "properties" in doc:
            raise SuperdeskApiError.badRequestError(
                message="Request is not valid",
                payload={"properties": "field is not supported when 'cpnat_type' is 'cpnat:abstract'"},
            )

    def _validate_event_properties(self, doc):
        # Step to implement validation(s):
        # 1) define schema_event in resource (https://iptc.org/std/NewsML-G2/guidelines/#more-real-world-entities)
        # 2) create cerberus Validator based on the schema_event
        # 3) validate doc['properties'] using cerberus Validator instance
        # TODO if we want to have a case insensitive sort, please, add a proper index

        raise SuperdeskApiError.badRequestError(
            message="Request is not valid", payload={"cpnat_type": "concept type 'cpnat:event' is not supported"}
        )

    def _validate_geoarea_properties(self, doc):
        raise SuperdeskApiError.badRequestError(
            message="Request is not valid", payload={"cpnat_type": "concept type 'cpnat:geoArea' is not supported"}
        )

    def _validate_object_properties(self, doc):
        raise SuperdeskApiError.badRequestError(
            message="Request is not valid", payload={"cpnat_type": "concept type 'cpnat:object' is not supported"}
        )

    def _validate_organisation_properties(self, doc):
        raise SuperdeskApiError.badRequestError(
            message="Request is not valid", payload={"cpnat_type": "concept type 'cpnat:organisation' is not supported"}
        )

    def _validate_person_properties(self, doc):
        raise SuperdeskApiError.badRequestError(
            message="Request is not valid", payload={"cpnat_type": "concept type 'cpnat:person' is not supported"}
        )

    def _validate_poi_properties(self, doc):
        raise SuperdeskApiError.badRequestError(
            message="Request is not valid", payload={"cpnat_type": "concept type 'cpnat:poi' is not supported"}
        )

    def _setup_created_by(self, doc, original=None):
        if not original:
            doc["created_by"] = get_user().get("_id")
        else:
            # for PUT request
            doc["created_by"] = original["created_by"]

    def _setup_updated_by(self, doc):
        doc["updated_by"] = get_user().get("_id")

    def _setup_group_id(self, doc):
        if "group_id" not in doc:
            doc["group_id"] = str(uuid4())
