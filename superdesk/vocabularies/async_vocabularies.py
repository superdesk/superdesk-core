# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import json
import logging
from typing import Annotated, Any, Dict, List, Optional
from typing import List

from eve.methods.common import serialize_value
from pydantic import BaseModel, ConfigDict, Field
from quart_babel import gettext as _, lazy_gettext

from superdesk import privilege
from superdesk.cache import cache
from superdesk.core.resources import ResourceModel, dataclass
from superdesk.core.resources.model import ResourceModel
from superdesk.core.resources.service import AsyncResourceService
from superdesk.core.resources.validators import validate_maxlength
from superdesk.core.types import SearchRequest
from superdesk.default_schema import DEFAULT_EDITOR, DEFAULT_SCHEMA
from superdesk.errors import SuperdeskApiError
from superdesk.flask import request
from superdesk.notification import push_notification
from superdesk.resource_fields import ID_FIELD
from superdesk.users import get_user_from_request
from superdesk.utc import utcnow

logger = logging.getLogger(__name__)

KEYWORDS_CV = "keywords"


privilege(
    name="vocabularies",
    label=lazy_gettext("Vocabularies Management"),
    description=lazy_gettext("User can manage vocabularies' contents."),
)


# TODO(petr): add api to specify vocabulary schema
vocab_schema = {
    "crop_sizes": {
        "width": {"type": "integer"},
        "height": {"type": "integer"},
    }
}


@dataclass
class Tag:
    text: str


class Item(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    qcode: str
    is_active: bool = True


@dataclass
class DateShortcut:
    value: int
    term: str
    label: str


@dataclass
class CustomFieldConfig:
    increment_steps: list[int]
    initial_offset_minutes: int


class VocabulariesResourceModel(ResourceModel):
    display_name: str
    description: str | None = None
    helper_text: Annotated[str | None, validate_maxlength(120)] = None
    tags: list[Tag] | None = None
    popup_width: int | None = None
    type_: str  # Use type_ instead of type due to reserved keyword conflict
    items: list[Item]
    selection_type: str | None = None
    read_only: bool | None = None
    schema_field: str | None = None
    dependent: bool = False
    service: dict[str, int] = Field(default_factory=dict)
    priority: int = 0
    unique_field: str | None = None
    schema_: dict[str, dict]
    field_type_: str | None = None
    field_options_: dict[str, Any] = Field(default_factory=dict)
    init_version: int = 0
    preffered_items: bool = False
    disable_entire_category_selection: bool = False
    date_shortcuts: list[DateShortcut] | None = None
    custom_field_type: str | None = None
    custom_field_config: CustomFieldConfig | None = None
    translations: dict[str, dict[str, Any]] = Field(default_factory=dict)


class VocabulariesService(AsyncResourceService[VocabulariesResourceModel]):
    system_keys = set(DEFAULT_SCHEMA.keys()).union(set(DEFAULT_EDITOR.keys()))

    async def _validate_items(self, update: VocabulariesResourceModel) -> None:
        # if we have qcode and not unique_field set, we want it to be qcode
        if update.schema_.get("qcode") and update.unique_field is None:
            update.unique_field = "qcode"

        unique_field = update.unique_field
        vocabs = {}
        if update.schema_ and update.items:
            for index, item in enumerate(update.items):
                for field, desc in update.schema_.items():
                    if (desc.get("required", False) or unique_field == field) and not getattr(item, field, None):
                        msg = f"Required {field} in item {index}"
                        payload = {"error": {"required_field": 1}, "params": {"field": field, "item": index}}
                        raise SuperdeskApiError.badRequestError(message=msg, payload=payload)

                    elif desc.get("link_vocab") and desc.get("link_field"):
                        if not vocabs.get(desc["link_vocab"]):
                            linked_vocab = await self.find_one(_id=desc["link_vocab"])
                            items = linked_vocab.items if linked_vocab else []
                            vocabs[desc["link_vocab"]] = [getattr(vocab, desc["link_field"], None) for vocab in items]

                        if (field_value := getattr(item, field, None)) and field_value not in vocabs[
                            desc["link_vocab"]
                        ]:
                            msg = '{} "{}={}" not found'.format(desc["link_vocab"], desc["link_field"], field_value)
                            payload = {"error": {"required_field": 1, "params": {"field": field, "item": index}}}
                            raise SuperdeskApiError.badRequestError(message=msg, payload=payload)

    async def on_create(self, docs: List[VocabulariesResourceModel]) -> None:
        for doc in docs:
            await self._validate_items(doc)

            if doc.field_type_ and doc.id in self.system_keys:
                raise SuperdeskApiError(message=f"{doc.id} is in use", payload={"_id": {"conflict": 1}})

            if await self.find_one(_id=doc.id, _deleted=True):
                raise SuperdeskApiError(
                    message=f"{doc.id} is used by deleted vocabulary", payload={"_id": {"deleted": 1}}
                )

    async def on_created(self, docs: List[VocabulariesResourceModel]):
        for doc in docs:
            self._send_notification(doc, event="vocabularies:created")

    async def on_replace(self, document: VocabulariesResourceModel, original: VocabulariesResourceModel) -> None:
        await self._validate_items(document)
        document.updated = utcnow()
        document.created = original.created or utcnow()
        logger.info(f"updating vocabulary item: {document.id}")

    async def on_fetched(self, doc: VocabulariesResourceModel) -> (VocabulariesResourceModel | None):
        """Overriding to filter out inactive vocabularies and pops out 'is_active' property from the response.

        It keeps it when requested for manageable vocabularies.
        """

        if request and hasattr(request, "args") and request.args.get("where"):
            where_clause = json.loads(request.args.get("where"))
            if where_clause.get("type") == "manageable":
                return doc

        for item in doc.items:
            self._filter_inactive_vocabularies(item)
            self._cast_items(item)

    async def on_fetched_item(self, doc: VocabulariesResourceModel):
        """
        Overriding to filter out inactive vocabularies and pops out 'is_active' property from the response.
        """
        self._filter_inactive_vocabularies(doc)
        self._cast_items(doc)

    async def on_update(self, updates: dict[str, Any], original: VocabulariesResourceModel) -> None:
        """Checks the duplicates if a unique field is defined"""
        if "items" in updates:
            # FIXME: `model_copy` doesn't validate updates, is it fine here?
            updated = original.model_copy(deep=True, update=updates)
            await self._validate_items(updated)
        if original.unique_field:
            self._check_uniqueness(updates.get("items", []), original.unique_field)

    async def on_updated(self, updates: dict[str, Any], original: VocabulariesResourceModel) -> None:
        """
        Overriding this to send notification about the replacement
        """
        self._send_notification(original)

    async def on_replaced(self, document: VocabulariesResourceModel, original: VocabulariesResourceModel):
        """
        Overriding this to send notification about the replacement
        """
        self._send_notification(document)

    async def on_delete(self, doc: VocabulariesResourceModel):
        """
        Overriding to validate vocabulary deletion
        """
        if not doc.field_type_:
            raise SuperdeskApiError.badRequestError("Default vocabularies cannot be deleted")

    def _check_uniqueness(self, items: list[dict[str, Any]], unique_field: str) -> None:
        """Checks the uniqueness if a unique field is defined

        :param items: list of items to check for uniqueness
        :param unique_field: name of the unique field
        """
        unique_values = set()
        for item in items:
            # compare only the active items
            if not item.get("is_active"):
                continue

            if not item.get(unique_field):
                raise SuperdeskApiError.badRequestError(f"{unique_field} cannot be empty")

            unique_value = str(item.get(unique_field)).upper()

            if unique_value in unique_values:
                raise SuperdeskApiError.badRequestError(
                    f"Value {item.get(unique_field)} for field {unique_field} is not unique"
                )

            unique_values.add(unique_value)

    def _filter_inactive_vocabularies(self, item: VocabulariesResourceModel) -> None:
        vocs = item.items
        item.items = [
            Item(**{k: v for k, v in voc.model_dump().items() if k != "is_active"}) for voc in vocs if voc.is_active
        ]

    def _cast_items(self, vocab: VocabulariesResourceModel) -> None:
        """Cast values in vocabulary items using predefined schema.

        :param vocab
        """
        # FIXME: This doesn't make sense
        schema = vocab_schema.get(vocab.id, {})
        for item in vocab.items:
            for field, field_schema in schema.items():
                if hasattr(item, field):
                    # FIXME: not sure about this one either.
                    setattr(item, field, serialize_value(field_schema["type"], getattr(item, field)))

    def _send_notification(self, updated_vocabulary: VocabulariesResourceModel, event="vocabularies:updated") -> None:
        """
        Sends notification about the updated vocabulary to all the connected clients.
        """

        user = get_user_from_request()
        push_notification(
            event,
            vocabulary=updated_vocabulary.display_name,
            user=str(user[ID_FIELD]) if user else None,
            vocabulary_id=updated_vocabulary.id,
        )

    async def get_rightsinfo(self, item: ResourceModel) -> dict[str, Any]:
        """Retrieve rights information for the given item.

        :param item: The item to retrieve rights information for
        :return: Dictionary containing copyright holder, notice and usage terms
        """
        rights_key = getattr(item, "source", getattr(item, "original_source", "default"))
        all_rights = await self.find_one(_id="rightsinfo")

        if not all_rights or not all_rights.items:
            return {}

        try:
            all_rights.items = await self.get_locale_vocabulary(all_rights.items, getattr(item, "language", None))
            default_rights = next(info for info in all_rights.items if getattr(info, "name", None) == "default")
        except StopIteration:
            default_rights = None

        try:
            rights = next(info for info in all_rights.items if getattr(info, "name", None) == rights_key)
        except StopIteration:
            rights = default_rights

        if rights:
            return {
                "copyrightholder": getattr(rights, "copyright_holder", None),
                "copyrightnotice": getattr(rights, "copyright_notice", None),
                "usageterms": getattr(rights, "usage_terms", None),
            }
        return {}

    async def get_extra_fields(self) -> list[VocabulariesResourceModel]:
        cursor = await self.search(lookup={"field_type": {"$exists": True, "$ne": None}}, use_mongo=True)
        return await cursor.to_list()

    async def get_custom_vocabularies(self) -> list[VocabulariesResourceModel]:
        cursor = await self.search(
            lookup={
                "field_type": None,
                "service": {"$exists": True},
            },
            use_mongo=True,
        )
        return await cursor.to_list()

    async def get_forbiden_custom_vocabularies(self) -> list[VocabulariesResourceModel]:
        cursor = await self.search(
            lookup={
                "field_type": None,
                "selection_type": "do not show",
                "service": {"$exists": True},
            },
            use_mongo=True,
        )
        return await cursor.to_list()

    async def get_locale_vocabulary(
        self, vocabulary: list[VocabulariesResourceModel], language: str
    ) -> list[VocabulariesResourceModel]:
        if not vocabulary or not language:
            return vocabulary
        locale_vocabulary = []
        for item in vocabulary:
            if not item.translations:
                locale_vocabulary.append(item)
                continue
            new_item = item.model_copy(deep=True)
            locale_vocabulary.append(new_item)
            for field, values in new_item.translations.items():
                if hasattr(new_item, field) and language in values:
                    setattr(new_item, field, values[language])
        return locale_vocabulary

    async def add_missing_keywords(self, keywords, language: str | None = None) -> None:
        # FIXME: language is not use here.
        if not keywords:
            return
        cv = await self.find_one(_id=KEYWORDS_CV)
        if cv:
            existing = {item.name.lower() for item in cv.items}
            missing = [keyword for keyword in keywords if keyword.lower() not in existing]
            if missing:
                updates = {"items": cv.items.copy()}
                for keyword in missing:
                    updates["items"].append(
                        Item(
                            name=keyword,
                            qcode=keyword,
                            is_active=True,
                        )
                    )
                await self.on_update(updates, cv)
                await self.system_update(cv.id, updates)
                await self.on_updated(updates, cv)
        else:
            items = [
                Item(
                    name=keyword,
                    qcode=keyword,
                    is_active=True,
                )
                for keyword in keywords
            ]
            cv = VocabulariesResourceModel(
                id=KEYWORDS_CV,
                items=items,
                type_="manageable",
                display_name=_("Keywords"),
                unique_field="name",
                schema_={
                    "name": {},
                    "qcode": {},
                },
            )
            await self.create([cv])

    async def get_article_cv_item(self, item: Dict[str, Any], scheme: str):
        article_item = {k: v for k, v in item.items() if k != "is_active"}
        article_item.update({"scheme": scheme})
        return article_item

    async def get_items(
        self,
        _id: str,
        qcode: Optional[str] = None,
        is_active: bool = True,
        name: Optional[str] = None,
        lang: Optional[str] = None,
    ) -> List[Item]:
        """
        Return `items` with specified filters from the CV with specified `_id`.
        If `lang` is provided then `name` is looked in `items.translations.name.{lang}`,
        otherwise `name` is looked in `items.name`.

        :param _id: custom vocabulary _id
        :param qcode: items.qcode filter
        :param is_active: items.is_active filter
        :param name: items.name filter
        :param lang: items.lang filter
        :return: items list
        """

        projection: dict[str, Any] = {}
        lookup = {"_id": _id}

        if qcode:
            elem_match = projection.setdefault("items", {}).setdefault("$elemMatch", {})
            elem_match["qcode"] = qcode

        # if `lang` is provided `name` is looked in `translations.name.{lang}`
        if name and lang:
            elem_match = projection.setdefault("items", {}).setdefault("$elemMatch", {})
            elem_match[f"translations.name.{lang}"] = {
                "$regex": r"^{}$".format(name),
                # case-insensitive
                "$options": "i",
            }
        elif name:
            elem_match = projection.setdefault("items", {}).setdefault("$elemMatch", {})
            elem_match["name"] = {
                "$regex": r"^{}$".format(name),
                # case-insensitive
                "$options": "i",
            }

        cursor = await self.find(SearchRequest(where=lookup, projection=projection))

        try:
            voc = await cursor.next()
            if voc is None:
                raise StopIteration
        except StopIteration:
            return []
        else:
            items = voc.items

        # $elemMatch projection contains only the first element matching the condition,
        # that"s why `is_active` filter is filtered via python
        if is_active is not None:
            items = [i for i in items if i.is_active == is_active]

        def format_item(item: Item) -> Item:
            try:
                del item.is_active
            except KeyError:
                pass
            # FIXME
            item.scheme = _id  # type: ignore
            return item

        items = list(map(format_item, items))

        return items

    async def get_languages(self) -> list[Item]:
        return await self.get_items(_id="languages")

    async def get_field_options(self, field) -> dict[str, Any]:
        cv = await self.find_one(_id=field)
        return cv.field_options_ if cv else {}


@cache(ttl=3600, tags=("vocabularies",))
async def get_related_field_ids():
    service = VocabulariesService()
    cursor = await service.find(
        req=SearchRequest(where={"field_type": "related_content"}, projection={"field_type": 1})
    )
    return await cursor.to_list()


def is_related_content(item_name, related_content=None):
    if related_content is None:
        related_content = get_related_field_ids()

    if related_content and item_name.split("--")[0] in [content["_id"] for content in related_content]:
        return True

    return False
