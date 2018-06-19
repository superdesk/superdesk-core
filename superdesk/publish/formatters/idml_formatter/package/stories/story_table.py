from lxml import etree

from .story import Story


class StoryTable(Story):
    """
    Story which represents `table` html tag.
    """

    TABLE_DEFAULTS = {
        'HeaderRowCount': '0',
        'FooterRowCount': '0',
        'AppliedTableStyle': 'TableStyle/$ID/[Basic Table]',
        'TableDirection': 'LeftToRightDirection'
    }
    CELL_DEFAULTS = {
        'CellType': 'TextTypeCell',
        'AppliedCellStyle': 'CellStyle/$ID/[None]'
    }

    def __init__(self, self_id, element, inner_page_width, attributes=None, markup_tag=None):
        self._inner_page_width = inner_page_width
        super().__init__(self_id, element, attributes, markup_tag)

    def _add_story(self):
        # merge Story attributes
        story_attributes = self.merge_attributes(
            self.STORY_DEFAULTS,
            self._attributes.get('Story', {})
        )
        story_attributes.update({'Self': self.self_id})
        # Story
        story = etree.SubElement(
            self._etree,
            'Story',
            attrib=story_attributes
        )

        if self._markup_tag:
            # XMLElement to tag a story
            table_container = etree.SubElement(
                story,
                'XMLElement',
                attrib={
                    'Self': '{}_{}'.format(self.self_id, self._markup_tag.lower()),
                    'XMLContent': self.self_id,
                    'MarkupTag': 'XMLTag/{}'.format(self._markup_tag)
                }
            )
        else:
            table_container = story

        # create Table and insert it into table_container
        table_container.insert(1, self._create_table())
        # StoryPreference
        etree.SubElement(
            story,
            'StoryPreference',
            attrib=self.merge_attributes(
                self.STORYPREFERENCE_DEFAULTS,
                self._attributes.get('StoryPreference', {})
            )
        )

        return story

    def _create_table(self):
        table_data = {}
        table_data['cells'] = self._element.xpath('.//td')
        table_data['rows_count'] = int(self._element.xpath('count(.//tr)'))
        table_data['columns_count'] = int(self._element.xpath('count(.//td)') / table_data['rows_count'])
        # Table
        table = etree.Element(
            'Table',
            attrib=self.merge_attributes(
                self.TABLE_DEFAULTS,
                self._attributes.get('Table', {})
            )
        )
        table.set('Self', '{}_table'.format(self.self_id))
        table.set('BodyRowCount', str(table_data['rows_count']))
        table.set('ColumnCount', str(table_data['columns_count']))
        # Row(s)
        for i in range(table_data['rows_count']):
            etree.SubElement(
                table,
                'Row',
                attrib={
                    'Self': '{}_table_row{}'.format(self.self_id, i),
                    'Name': str(i)
                }
            )
        # Column(s)
        column_width = self._inner_page_width / table_data['columns_count']
        for i in range(table_data['columns_count']):
            etree.SubElement(
                table,
                'Column',
                attrib={
                    'Self': '{}_table_column{}'.format(self.self_id, i),
                    'Name': str(i),
                    'SingleColumnWidth': str(column_width)
                }
            )
        # Cells
        cell_counter = 0
        for r in range(table_data['rows_count']):
            for c in range(table_data['columns_count']):
                # Cell
                cell = etree.SubElement(
                    table,
                    'Cell',
                    attrib=self.merge_attributes(
                        self.CELL_DEFAULTS,
                        {
                            'Self': '{}_table_i{}'.format(self.self_id, cell_counter),
                            'Name': '{cell}:{row}'.format(cell=c, row=r),
                        }
                    )
                )
                # CharacterStyleRange(s) + <Br />
                for p in table_data['cells'][cell_counter].xpath('.//p'):
                    if cell.find('CharacterStyleRange') is not None:
                        etree.SubElement(
                            cell,
                            'Br'
                        )
                    cell[:] += self._handle_inline_tags(p)
                cell_counter += 1

        return table

    @property
    def length(self):
        raise NotImplementedError

    @staticmethod
    def guess_height(story, inner_width):
        table_height = 0
        table_element = story._etree.xpath('.//Table')[0]
        column_count = int(table_element.get('ColumnCount'))
        row_count = int(table_element.get('BodyRowCount'))

        for row_number in range(row_count):
            highest_cell_len = None

            for column_number in range(column_count):
                try:
                    cell = story._etree.xpath('.//Cell[@Name="{}:{}"]'.format(column_number, row_number))[0]
                except IndexError:
                    continue
                else:
                    current_cell_len = 0

                    for content in cell.xpath('.//Content'):
                        current_cell_len += len(" ".join(etree.XPath(".//text()")(content)).strip())

                    if not highest_cell_len or current_cell_len > highest_cell_len:
                        highest_cell_len = current_cell_len

            row_height = highest_cell_len / (inner_width / column_count) * 90 + 10

            if row_height < 20:
                row_height = 20
            table_height += row_height

        return table_height
