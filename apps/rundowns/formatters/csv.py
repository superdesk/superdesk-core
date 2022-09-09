from . import BaseFormatter, utils


class TableCSVFormatter(BaseFormatter):

    MIMETYPE = "text/csv"
    SEPARATOR = "\t"
    COLUMNS = [
        "Order",
        "Type",
        "Title",
        "Tone/Off",
        "Additional realizer info",
        "Live Captions",
        "Part of the last spoken sentence",
        "Duration",
    ]

    def export(self, show, rundown, items):
        filename = f"Realizer-{rundown['title']}.csv"
        data = "\n".join(
            [self.SEPARATOR.join(self.COLUMNS)]
            + [
                self.SEPARATOR.join(utils.item_table_data(show, rundown, item, i))
                for i, item in enumerate(items, start=1)
            ]
        )
        return data.encode("utf-8"), self.MIMETYPE, filename
