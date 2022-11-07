from . import BaseFormatter, utils


class TableCSVFormatter(BaseFormatter):

    MIMETYPE = "text/csv"
    SEPARATOR = "\t"
    COLUMNS = [
        "Order",
        "Type",
        "Technical Title",
        "Additional realizer info",
        "Duration",
    ]

    def export(self, show, rundown, items):
        filename = f"Technical-{rundown['title']}.csv"
        data = "\n".join(
            [self.SEPARATOR.join(self.COLUMNS)]
            + [
                self.SEPARATOR.join(utils.item_table_data(show, rundown, item, i))
                for i, item in enumerate(items, start=1)
            ]
        )
        return data.encode("utf-8"), self.MIMETYPE, filename
