from lxml import etree

from .story import Story


class StoryList(Story):
    """
    Story which represents `ul`, `ol` html tags.
    """

    def _add_story(self):
        # merge Story attributes
        story_attributes = self.merge_attributes(self.STORY_DEFAULTS, self._attributes.get("Story", {}))
        story_attributes.update({"Self": self.self_id})
        # Story
        story = etree.SubElement(self._etree, "Story", attrib=story_attributes)
        # StoryPreference
        etree.SubElement(
            story,
            "StoryPreference",
            attrib=self.merge_attributes(self.STORYPREFERENCE_DEFAULTS, self._attributes.get("StoryPreference", {})),
        )

        if self._markup_tag:
            # XMLElement to tag a story
            paragraphstylerange_container = etree.SubElement(
                story,
                "XMLElement",
                attrib={
                    "Self": "{}_{}".format(self.self_id, self._markup_tag.lower()),
                    "XMLContent": self.self_id,
                    "MarkupTag": "XMLTag/{}".format(self._markup_tag),
                },
            )
        else:
            paragraphstylerange_container = story

        # ParagraphStyleRange
        paragraphstylerange = etree.SubElement(
            paragraphstylerange_container,
            "ParagraphStyleRange",
            attrib=self.merge_attributes(
                self.PARAGRAPHSTYLERANGE_DEFAULTS, self._attributes.get("ParagraphStyleRange", {})
            ),
        )

        # CharacterStyleRange(s) + <Br />
        for li in self._element.xpath(".//li"):
            if paragraphstylerange.find("CharacterStyleRange") is not None:
                etree.SubElement(paragraphstylerange, "Br")
            paragraphstylerange[:] += self._handle_inline_tags(li)

        return story

    @property
    def length(self):
        raise NotImplementedError

    @staticmethod
    def guess_height(story, inner_width):
        list_height = 0
        list_item_length = 0
        list_item_height = 0

        for el in story._etree.xpath(".//ParagraphStyleRange")[0].iterchildren():

            if el.tag == "Br":
                if list_item_height < 20:
                    list_item_height = 20
                list_height += list_item_height
                # next list item
                list_item_length = 0
                list_item_height = 0
            else:
                list_item_length += len(" ".join(etree.XPath(".//text()")(el)).strip())
                list_item_height += list_item_length / inner_width * 70

        return list_height + 10
