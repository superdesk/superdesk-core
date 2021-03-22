#!/usr/bin/env python3
# This file is part of Superdesk.
#
# Copyright 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Unit tests for editor utils"""

import json
import uuid
import unittest
import flask
import superdesk.editor_utils as editor_utils

from superdesk.editor_utils import Editor3Content


class Editor3TestCase(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.app = flask.Flask(__name__)
        self.app.app_context().push()
        super().setUp()
        if "EMBED_PRE_PROCESS" in self.app.config:
            del self.app.config["EMBED_PRE_PROCESS"]

    def build_item(self, draftjs_data, field="body_html"):
        return {
            "fields_meta": {
                field: {
                    "draftjsState": [draftjs_data],
                },
            },
        }

    def update_item_field(self, item, draftjs_data, field):
        item["fields_meta"][field] = {"draftjsState": [draftjs_data]}

    def blocks_with_text(self, data_list):
        draftjs_data = {
            "blocks": [],
            "entityMap": {},
        }
        blocks = draftjs_data["blocks"]
        for item_data in data_list:
            type_, depth, text = item_data
            blocks.append(
                {
                    "key": str(uuid.uuid4()),
                    "text": text,
                    "type": type_,
                    "depth": depth,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                }
            )
        return draftjs_data

    def create_table(self, cols, rows, cells, with_header=False):
        cells_list = []
        draftjs_data = {
            "blocks": [
                {
                    "key": "first_block",
                    "text": "",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "table_key",
                    "text": " ",
                    "type": "atomic",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [{"offset": 0, "length": 1, "key": 0}],
                    "data": {},
                },
                {
                    "key": "last_block",
                    "text": "",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
            ],
            "entityMap": {
                "0": {
                    "type": "TABLE",
                    "mutability": "MUTABLE",
                    "data": {
                        "data": {
                            "cells": cells_list,
                            "numCols": cols,
                            "numRows": rows,
                            "withHeader": with_header,
                        }
                    },
                }
            },
        }

        for cell_row in cells:
            row = []
            cells_list.append(row)
            for cell in cell_row:
                row.append(
                    {
                        "blocks": [
                            {
                                "key": str(uuid.uuid4()),
                                "text": cell,
                                "type": "unstyled",
                                "depth": 0,
                                "inlineStyleRanges": [],
                                "entityRanges": [],
                                "data": {},
                            }
                        ],
                        "entityMap": {},
                    }
                    if cell
                    else None
                )

        draftjs_data["blocks"][0]["data"]["data"] = json.dumps(draftjs_data["entityMap"]["0"]["data"]["data"])
        return draftjs_data

    def test_no_formatting(self):
        """Check that a sentence without formatting can generate HTML"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": 'The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".',
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                }
            ],
            "entityMap": {},
        }
        expected = '<p>The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".</p>'

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_simple_inline_styles(self):
        """Check that a sentence with simple inline styles can generate HTML"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": 'The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".',
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [
                        {"offset": 0, "length": 3, "style": "BOLD"},
                        {"offset": 4, "length": 4, "style": "ITALIC"},
                        {"offset": 9, "length": 2, "style": "UNDERLINE"},
                        {"offset": 12, "length": 8, "style": "STRIKETHROUGH"},
                        {"offset": 21, "length": 5, "style": "SUBSCRIPT"},
                        {"offset": 27, "length": 4, "style": "SUPERSCRIPT"},
                    ],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                }
            ],
            "entityMap": {},
        }

        expected = (
            "<p><b>The</b> <i>name</i> <u>of</u> <s>Highlaws</s> <sub>comes</sub> <sup>from</sup> the Old English "
            'hēah-hlāw, meaning "high mounds".</p>'
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_heading(self):
        """Check that headlines are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": "The name of Highlaws comes from the Old English hēah-hlāw",
                    "type": "header-one",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "32mrs",
                    "text": ', meaning "high mounds". In the past,',
                    "type": "header-two",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
                {
                    "key": "d2ggv",
                    "text": "variant spellings included Heelawes, Hielawes,",
                    "type": "header-three",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
                {
                    "key": "3eqv5",
                    "text": "Highlows, Hielows, and Hylaws.",
                    "type": "header-four",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
                {
                    "key": "8lcpm",
                    "text": "[2] The hamlet appears in a survey of Holm Cultram dating back",
                    "type": "header-five",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
                {
                    "key": "emuqc",
                    "text": "to the year 1538, during the reign of Henry VIII.",
                    "type": "header-six",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
                {
                    "key": "90o9n",
                    "text": "There were at least thirteen families resident in Highlaws at that time.[3] Abdastartus "
                    "is a genus of lace bugs in the family Tingidae. There are about five described species in "
                    "Abdastartus.",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
            ],
            "entityMap": {},
        }

        expected = (
            "<h1>The name of Highlaws comes from the Old English hēah-hlāw</h1>\n"
            '<h2>, meaning "high mounds". In the past,</h2>\n'
            "<h3>variant spellings included Heelawes, Hielawes,</h3>\n"
            "<h4>Highlows, Hielows, and Hylaws.</h4>\n"
            "<h5>[2] The hamlet appears in a survey of Holm Cultram dating back</h5>\n"
            "<h6>to the year 1538, during the reign of Henry VIII.</h6>\n"
            "<p>There were at least thirteen families resident in Highlaws at that time.[3] Abdastartus "
            "is a genus of lace bugs in the family Tingidae. There are about five described species in Abdastartus.</p>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_blockquote(self):
        """Check that blockqotes are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": 'The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".',
                    "type": "blockquote",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "2u79k",
                    "text": "In the past, variant spellings included Heelawes, Hielawes, Highlows, Hielows, and "
                    "Hylaws.",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
            ],
            "entityMap": {},
        }

        expected = (
            '<blockquote>The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".</blockquote>\n'
            "<p>In the past, variant spellings included Heelawes, Hielawes, Highlows, Hielows, and Hylaws.</p>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_code_blocks(self):
        """Check that code blocks are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": 'The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".',
                    "type": "code-block",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "2u79k",
                    "text": "In the past, variant spellings included Heelawes, Hielawes, Highlows, Hielows, and "
                    "Hylaws.",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
            ],
            "entityMap": {},
        }

        expected = (
            '<pre><code>The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".</code></pre>\n'
            "<p>In the past, variant spellings included Heelawes, Hielawes, Highlows, Hielows, and Hylaws.</p>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_links(self):
        """Check that links are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": 'The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".',
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [{"offset": 12, "length": 8, "key": 0}],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                }
            ],
            "entityMap": {
                "0": {
                    "type": "LINK",
                    "mutability": "MUTABLE",
                    "data": {"link": {"href": "https://en.wikipedia.org/wiki/Highlaws"}},
                }
            },
        }

        expected = (
            '<p>The name of <a href="https://en.wikipedia.org/wiki/Highlaws">Highlaws</a> comes from the Old English hē'
            'ah-hlāw, meaning "high mounds".</p>'
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_simple_table(self):
        """Check that a simple table is converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": "",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "fhokc",
                    "text": " ",
                    "type": "atomic",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [{"offset": 0, "length": 1, "key": 0}],
                    "data": {
                        "data": '{"cells":[[{"blocks":[{"key":"k8sb","text":"three","type":"unstyled","depth":0,"inline'
                        'StyleRanges":[],"entityRanges":[],"data":{}}],"entityMap":{}},{"blocks":[{"key":"a25i9'
                        '","text":"column","type":"unstyled","depth":0,"inlineStyleRanges":[],"entityRanges":[]'
                        ',"data":{}}],"entityMap":{}},{"blocks":[{"key":"ej3lv","text":"table","type":"unstyled'
                        '","depth":0,"inlineStyleRanges":[],"entityRanges":[],"data":{}}],"entityMap":{}}],[{"b'
                        'locks":[{"key":"f0qc0","text":"example","type":"unstyled","depth":0,"inlineStyleRanges'
                        '":[],"entityRanges":[],"data":{}}],"entityMap":{}},{"blocks":[{"key":"50s2o","text":"r'
                        'ight","type":"unstyled","depth":0,"inlineStyleRanges":[],"entityRanges":[],"data":{}}]'
                        ',"entityMap":{}},{"blocks":[{"key":"escgd","text":"here","type":"unstyled","depth":0,"'
                        'inlineStyleRanges":[],"entityRanges":[],"data":{}}],"entityMap":{}}]],"numRows":2,"num'
                        'Cols":3,"withHeader":false}'
                    },
                },
                {
                    "key": "2u79k",
                    "text": "",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
            ],
            "entityMap": {
                "0": {
                    "type": "TABLE",
                    "mutability": "MUTABLE",
                    "data": {
                        "data": {
                            "cells": [
                                [
                                    {
                                        "blocks": [
                                            {
                                                "key": "k8sb",
                                                "text": "three",
                                                "type": "unstyled",
                                                "depth": 0,
                                                "inlineStyleRanges": [],
                                                "entityRanges": [],
                                                "data": {},
                                            }
                                        ],
                                        "entityMap": {},
                                    },
                                    {
                                        "blocks": [
                                            {
                                                "key": "a25i9",
                                                "text": "column",
                                                "type": "unstyled",
                                                "depth": 0,
                                                "inlineStyleRanges": [],
                                                "entityRanges": [],
                                                "data": {},
                                            }
                                        ],
                                        "entityMap": {},
                                    },
                                    {
                                        "blocks": [
                                            {
                                                "key": "ej3lv",
                                                "text": "table",
                                                "type": "unstyled",
                                                "depth": 0,
                                                "inlineStyleRanges": [],
                                                "entityRanges": [],
                                                "data": {},
                                            }
                                        ],
                                        "entityMap": {},
                                    },
                                ],
                                [
                                    {
                                        "blocks": [
                                            {
                                                "key": "f0qc0",
                                                "text": "example",
                                                "type": "unstyled",
                                                "depth": 0,
                                                "inlineStyleRanges": [],
                                                "entityRanges": [],
                                                "data": {},
                                            }
                                        ],
                                        "entityMap": {},
                                    },
                                    {
                                        "blocks": [
                                            {
                                                "key": "50s2o",
                                                "text": "right",
                                                "type": "unstyled",
                                                "depth": 0,
                                                "inlineStyleRanges": [],
                                                "entityRanges": [],
                                                "data": {},
                                            }
                                        ],
                                        "entityMap": {},
                                    },
                                    {
                                        "blocks": [
                                            {
                                                "key": "escgd",
                                                "text": "here",
                                                "type": "unstyled",
                                                "depth": 0,
                                                "inlineStyleRanges": [],
                                                "entityRanges": [],
                                                "data": {},
                                            }
                                        ],
                                        "entityMap": {},
                                    },
                                ],
                            ],
                            "numRows": 2,
                            "numCols": 3,
                            "withHeader": False,
                        }
                    },
                }
            },
        }

        expected = (
            "<table><tbody><tr><td><p>three</p></td><td><p>column</p></td><td><p>table</p></td></tr><tr><td><p>example<"
            "/p></td><td><p>right</p></td><td><p>here</p></td></tr></tbody></table>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_table_inline_styles(self):
        """Check that tables with inline styles are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": "",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "fhokc",
                    "text": " ",
                    "type": "atomic",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [{"offset": 0, "length": 1, "key": 0}],
                    "data": {
                        "data": '{"cells":[[{"blocks":[{"key":"k8sb","text":"three","type":"unstyled","depth":0,"inline'
                        'StyleRanges":[{"offset":0,"length":5,"style":"BOLD"}],"entityRanges":[],"data":{}}],"e'
                        'ntityMap":{}},{"blocks":[{"key":"a25i9","text":"column","type":"unstyled","depth":0,"i'
                        'nlineStyleRanges":[{"offset":0,"length":6,"style":"ITALIC"}],"entityRanges":[],"data":'
                        '{}}],"entityMap":{}},{"blocks":[{"key":"ej3lv","text":"table","type":"unstyled","depth'
                        '":0,"inlineStyleRanges":[{"offset":0,"length":5,"style":"UNDERLINE"}],"entityRanges":['
                        '],"data":{}}],"entityMap":{}}],[{"blocks":[{"key":"f0qc0","text":"example","type":"uns'
                        'tyled","depth":0,"inlineStyleRanges":[{"offset":0,"length":7,"style":"SUBSCRIPT"}],"en'
                        'tityRanges":[],"data":{}}],"entityMap":{}},{"blocks":[{"key":"50s2o","text":"right","t'
                        'ype":"unstyled","depth":0,"inlineStyleRanges":[{"offset":0,"length":5,"style":"SUPERSC'
                        'RIPT"}],"entityRanges":[],"data":{}}],"entityMap":{}},{"blocks":[{"key":"escgd","text"'
                        ':"here","type":"unstyled","depth":0,"inlineStyleRanges":[{"offset":0,"length":4,"style'
                        '":"STRIKETHROUGH"}],"entityRanges":[],"data":{}}],"entityMap":{}}]],"numRows":2,"numCo'
                        'ls":3,"withHeader":false}'
                    },
                },
                {
                    "key": "2u79k",
                    "text": "",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
            ],
            "entityMap": {
                "0": {
                    "type": "TABLE",
                    "mutability": "MUTABLE",
                    "data": {
                        "data": {
                            "cells": [
                                [
                                    {
                                        "blocks": [
                                            {
                                                "key": "k8sb",
                                                "text": "three",
                                                "type": "unstyled",
                                                "depth": 0,
                                                "inlineStyleRanges": [{"offset": 0, "length": 5, "style": "BOLD"}],
                                                "entityRanges": [],
                                                "data": {},
                                            }
                                        ],
                                        "entityMap": {},
                                    },
                                    {
                                        "blocks": [
                                            {
                                                "key": "a25i9",
                                                "text": "column",
                                                "type": "unstyled",
                                                "depth": 0,
                                                "inlineStyleRanges": [{"offset": 0, "length": 6, "style": "ITALIC"}],
                                                "entityRanges": [],
                                                "data": {},
                                            }
                                        ],
                                        "entityMap": {},
                                    },
                                    {
                                        "blocks": [
                                            {
                                                "key": "ej3lv",
                                                "text": "table",
                                                "type": "unstyled",
                                                "depth": 0,
                                                "inlineStyleRanges": [{"offset": 0, "length": 5, "style": "UNDERLINE"}],
                                                "entityRanges": [],
                                                "data": {},
                                            }
                                        ],
                                        "entityMap": {},
                                    },
                                ],
                                [
                                    {
                                        "blocks": [
                                            {
                                                "key": "f0qc0",
                                                "text": "example",
                                                "type": "unstyled",
                                                "depth": 0,
                                                "inlineStyleRanges": [{"offset": 0, "length": 7, "style": "SUBSCRIPT"}],
                                                "entityRanges": [],
                                                "data": {},
                                            }
                                        ],
                                        "entityMap": {},
                                    },
                                    {
                                        "blocks": [
                                            {
                                                "key": "50s2o",
                                                "text": "right",
                                                "type": "unstyled",
                                                "depth": 0,
                                                "inlineStyleRanges": [
                                                    {"offset": 0, "length": 5, "style": "SUPERSCRIPT"}
                                                ],
                                                "entityRanges": [],
                                                "data": {},
                                            }
                                        ],
                                        "entityMap": {},
                                    },
                                    {
                                        "blocks": [
                                            {
                                                "key": "escgd",
                                                "text": "here",
                                                "type": "unstyled",
                                                "depth": 0,
                                                "inlineStyleRanges": [
                                                    {"offset": 0, "length": 4, "style": "STRIKETHROUGH"}
                                                ],
                                                "entityRanges": [],
                                                "data": {},
                                            }
                                        ],
                                        "entityMap": {},
                                    },
                                ],
                            ],
                            "numRows": 2,
                            "numCols": 3,
                            "withHeader": False,
                        }
                    },
                }
            },
        }

        expected = (
            "<table><tbody><tr><td><p><b>three</b></p></td><td><p><i>column</i></p></td><td><p><u>table</u></p></td></t"
            "r><tr><td><p><sub>example</sub></p></td><td><p><sup>right</sup></p></td><td><p><s>here</s></p></td></tr></"
            "tbody></table>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_table_none(self):
        """Check that a table with None value in a cell is generated correctly"""

        draftjs_data = self.create_table(
            cols=3,
            rows=2,
            cells=[
                ["a", None, "c"],
                ["d", "e", "f"],
            ],
        )

        expected = (
            "<table><tbody><tr><td><p>a</p></td><td></td><td><p>c</p></td></tr><tr><td><p>d</p></td><td><p>e</p></td><t"
            "d><p>f</p></td></tr></tbody></table>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_table_single(self):
        """Check that a table with a single row is generated correctly"""

        draftjs_data = self.create_table(
            cols=3,
            rows=1,
            cells=[
                ["a", "b", "c"],
            ],
        )

        expected = "<table><tbody><tr><td><p>a</p></td><td><p>b</p></td><td><p>c</p></td></tr></tbody></table>"

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_table_header(self):
        """Check that a table with header is generated correctly"""

        draftjs_data = self.create_table(
            cols=3,
            rows=3,
            with_header=True,
            cells=[
                ["a", None, "c"],
                ["d", "e", "f"],
                ["g", "h", "i"],
            ],
        )

        expected = (
            "<table><thead><tr><th><p>a</p></th><th></th><th><p>c</p></th></tr></thead><tbody><tr><td><p>d</p></td><td>"
            "<p>e</p></td><td><p>f</p></td></tr><tr><td><p>g</p></td><td><p>h</p></td><td><p>i</p></td></tr></tbody></t"
            "able>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_table_header_single_row(self):
        """Check that a table with header and single row is generated correctly"""

        draftjs_data = self.create_table(
            cols=3,
            rows=1,
            with_header=True,
            cells=[
                ["a", "b", "c"],
            ],
        )

        expected = "<table><thead><tr><th><p>a</p></th><th><p>b</p></th><th><p>c</p></th></tr></thead></table>"

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_table_empty(self):
        """Check that an empty table is generated correctly"""

        draftjs_data = self.create_table(
            cols=3,
            rows=2,
            cells=[],
        )

        expected = (
            "<table><tbody><tr><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td></tr></tbody></table>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_image(self):
        """Check that images are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": "",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "fi1d",
                    "text": " ",
                    "type": "atomic",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [{"offset": 0, "length": 1, "key": 0}],
                    "data": {},
                },
                {
                    "key": "60vvd",
                    "text": "",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
            ],
            "entityMap": {
                "0": {
                    "type": "MEDIA",
                    "mutability": "MUTABLE",
                    "data": {
                        "media": {
                            "flags": {
                                "marked_for_not_publication": False,
                                "marked_for_sms": False,
                                "marked_archived_only": False,
                                "marked_for_legal": False,
                            },
                            "language": "en",
                            "_updated": "2019-03-28T17:26:54+0000",
                            "description_text": "pin dec",
                            "source": "Superdesk",
                            "type": "picture",
                            "priority": 6,
                            "_current_version": 2,
                            "versioncreated": "2019-03-28T17:26:54+0000",
                            "task": {
                                "stage": "5c374805149f116db6aae6ad",
                                "user": "5acb79292e03ed5d2a84bbd6",
                                "desk": "5c374805149f116db6aae6af",
                            },
                            "urgency": 3,
                            "alt_text": "pin alt",
                            "_created": "2019-03-28T17:26:53+0000",
                            "genre": [{"name": "Article (news)", "qcode": "Article"}],
                            "guid": "tag:localhost:5000:2019:9df37ab0-4d96-4f95-8da5-06b744ef8604",
                            "renditions": {
                                "baseImage": {
                                    "width": 933,
                                    "mimetype": "image/jpeg",
                                    "href": "http://localhost:5000/api/upload-raw/5c9d03de149f116747b67317.jpg",
                                    "media": "5c9d03de149f116747b67317",
                                    "height": 1400,
                                },
                                "thumbnail": {
                                    "width": 79,
                                    "mimetype": "image/jpeg",
                                    "href": "http://localhost:5000/api/upload-raw/5c9d03de149f116747b67319.jpg",
                                    "media": "5c9d03de149f116747b67319",
                                    "height": 120,
                                },
                                "viewImage": {
                                    "width": 426,
                                    "mimetype": "image/jpeg",
                                    "href": "http://localhost:5000/api/upload-raw/5c9d03de149f116747b6731b.jpg",
                                    "media": "5c9d03de149f116747b6731b",
                                    "height": 640,
                                },
                                "original": {
                                    "width": 3648,
                                    "mimetype": "image/jpeg",
                                    "href": "http://localhost:5000/api/upload-raw/5c9d03dd149f116747b6730f.jpg",
                                    "media": "5c9d03dd149f116747b6730f",
                                    "height": 5472,
                                },
                            },
                            "state": "in_progress",
                            "expiry": None,
                            "byline": None,
                            "headline": "A picture of pineapple",
                            "_etag": "a2c443900319548148e9073b9c5cc4c76c9331c5",
                            "_id": "urn:newsml:localhost:5000:2019-03-28T18:26:53.805271:f47e37fd-a6bd-4a5e-b91d-01b581"
                            "f04e8c",
                            "_type": "archive",
                            "_links": {
                                "self": {
                                    "title": "Archive",
                                    "href": "archive/urn:newsml:localhost:5000:2019-03-28T18:26:53.805271:f47e37fd-a6bd"
                                    "-4a5e-b91d-01b581f04e8c",
                                }
                            },
                            "_latest_version": 2,
                            "selected": False,
                        }
                    },
                }
            },
        }

        expected = (
            '<!-- EMBED START Image {id: "editor_0"} -->\n'
            "<figure>"
            '<img src="http://localhost:5000/api/upload-raw/5c9d03dd149f116747b6730f.jpg" alt="pin alt">'
            "<figcaption>pin dec</figcaption></figure>\n"
            '<!-- EMBED END Image {id: "editor_0"} -->'
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_image_without_alt_and_desc(self):
        """Check that images without alt text and description are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": "",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "fi1d",
                    "text": " ",
                    "type": "atomic",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [{"offset": 0, "length": 1, "key": 0}],
                    "data": {},
                },
                {
                    "key": "60vvd",
                    "text": "",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
            ],
            "entityMap": {
                "0": {
                    "type": "MEDIA",
                    "mutability": "MUTABLE",
                    "data": {
                        "media": {
                            "flags": {
                                "marked_for_not_publication": False,
                                "marked_for_sms": False,
                                "marked_archived_only": False,
                                "marked_for_legal": False,
                            },
                            "language": "en",
                            "_updated": "2019-03-28T17:26:54+0000",
                            "source": "Superdesk",
                            "type": "picture",
                            "priority": 6,
                            "_current_version": 2,
                            "versioncreated": "2019-03-28T17:26:54+0000",
                            "task": {
                                "stage": "5c374805149f116db6aae6ad",
                                "user": "5acb79292e03ed5d2a84bbd6",
                                "desk": "5c374805149f116db6aae6af",
                            },
                            "urgency": 3,
                            "_created": "2019-03-28T17:26:53+0000",
                            "genre": [{"name": "Article (news)", "qcode": "Article"}],
                            "guid": "tag:localhost:5000:2019:9df37ab0-4d96-4f95-8da5-06b744ef8604",
                            "renditions": {
                                "baseImage": {
                                    "width": 933,
                                    "mimetype": "image/jpeg",
                                    "href": "http://localhost:5000/api/upload-raw/5c9d03de149f116747b67317.jpg",
                                    "media": "5c9d03de149f116747b67317",
                                    "height": 1400,
                                },
                                "thumbnail": {
                                    "width": 79,
                                    "mimetype": "image/jpeg",
                                    "href": "http://localhost:5000/api/upload-raw/5c9d03de149f116747b67319.jpg",
                                    "media": "5c9d03de149f116747b67319",
                                    "height": 120,
                                },
                                "viewImage": {
                                    "width": 426,
                                    "mimetype": "image/jpeg",
                                    "href": "http://localhost:5000/api/upload-raw/5c9d03de149f116747b6731b.jpg",
                                    "media": "5c9d03de149f116747b6731b",
                                    "height": 640,
                                },
                                "original": {
                                    "width": 3648,
                                    "mimetype": "image/jpeg",
                                    "href": "http://localhost:5000/api/upload-raw/5c9d03dd149f116747b6730f.jpg",
                                    "media": "5c9d03dd149f116747b6730f",
                                    "height": 5472,
                                },
                            },
                            "state": "in_progress",
                            "expiry": None,
                            "byline": None,
                            "headline": "A picture of pineapple",
                            "_etag": "a2c443900319548148e9073b9c5cc4c76c9331c5",
                            "_id": "urn:newsml:localhost:5000:2019-03-28T18:26:53.805271:f47e37fd-a6bd-4a5e-b91d-01b581"
                            "f04e8c",
                            "_type": "archive",
                            "_links": {
                                "self": {
                                    "title": "Archive",
                                    "href": "archive/urn:newsml:localhost:5000:2019-03-28T18:26:53.805271:f47e37fd-a6bd"
                                    "-4a5e-b91d-01b581f04e8c",
                                }
                            },
                            "_latest_version": 2,
                            "selected": False,
                        }
                    },
                }
            },
        }

        expected = (
            '<!-- EMBED START Image {id: "editor_0"} -->\n'
            '<figure><img src="http://localhost:5000/api/upload-raw/5c9d03dd149f116747b6730f.jpg" alt="">'
            "</figure>\n"
            '<!-- EMBED END Image {id: "editor_0"} -->'
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_unordered_list(self):
        """Check that unordered lists are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": "The name of",
                    "type": "unordered-list-item",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "fgkp6",
                    "text": "Highlaws comes",
                    "type": "unordered-list-item",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
                {
                    "key": "6g9h6",
                    "text": "from the Old English",
                    "type": "unordered-list-item",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
                {
                    "key": "7v7b1",
                    "text": "hēah-hlāw",
                    "type": "unordered-list-item",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
            ],
            "entityMap": {},
        }

        expected = "<ul><li>The name of</li><li>Highlaws comes</li><li>from the Old English</li><li>hēah-hlāw</li></ul>"

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_ordered_list(self):
        """Check that ordered lists are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": "The name of",
                    "type": "ordered-list-item",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "fgkp6",
                    "text": "Highlaws comes",
                    "type": "ordered-list-item",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
                {
                    "key": "6g9h6",
                    "text": "from the Old English",
                    "type": "ordered-list-item",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
                {
                    "key": "7v7b1",
                    "text": "hēah-hlāw",
                    "type": "ordered-list-item",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
            ],
            "entityMap": {},
        }

        expected = "<ol><li>The name of</li><li>Highlaws comes</li><li>from the Old English</li><li>hēah-hlāw</li></ol>"

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_mixing_ordered_unordered_lists(self):
        """Check that a mix of ordered and unordered lists are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": "The name of Highlaws comes from the Old English",
                    "type": "ordered-list-item",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "6oe0d",
                    "text": 'hēah-hlāw, meaning "high mounds". In the past, variant',
                    "type": "unordered-list-item",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
                {
                    "key": "aegg",
                    "text": "spellings included Heelawes, Hielawes, Highlows,",
                    "type": "ordered-list-item",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
                {
                    "key": "a1qv7",
                    "text": "Hielows, and Hylaws.",
                    "type": "ordered-list-item",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
            ],
            "entityMap": {},
        }

        expected = (
            "<ol><li>The name of Highlaws comes from the Old English</li></ol>\n"
            '<ul><li>hēah-hlāw, meaning "high mounds". In the past, variant</li></ul>\n'
            "<ol><li>spellings included Heelawes, Hielawes, Highlows,</li><li>Hielows, a"
            "nd Hylaws.</li></ol>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_embed(self):
        """Check that an embed is converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": "",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "2s495",
                    "text": " ",
                    "type": "atomic",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [{"offset": 0, "length": 1, "key": 0}],
                    "data": {},
                },
                {
                    "key": "egj1u",
                    "text": "",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                },
            ],
            "entityMap": {
                "0": {
                    "type": "EMBED",
                    "mutability": "MUTABLE",
                    "data": {
                        "data": {
                            "url": "https://www.youtube.com/watch?v=G5-KJgVsoUM",
                            "type": "video",
                            "version": "1.0",
                            "title": "Mother Mother - It's Alright",
                            "author": "MotherMotherVEVO",
                            "author_url": "https://www.youtube.com/channel/UCVzJrFuVWzf8mPiuV3o2_pQ",
                            "provider_name": "YouTube",
                            "description": "Music video by Mother Mother performing It's Alright. © 2019 Mother Mother Music Inc.,"
                            " under exclusive license to Universal Music Canada Inc.\\n\\nhttp://vevo.ly/V49vkg\n",
                            "thumbnail_url": "https://i.ytimg.com/vi/G5-KJgVsoUM/maxresdefault.jpg",
                            "thumbnail_width": 1280,
                            "thumbnail_height": 720,
                            "html": '<div><div style="left: 0; width: 100%; height: 0; position: relative; padding-bottom: '
                            '56.2493%;"><iframe src="//cdn.iframe.ly/api/iframe?url=https%3A%2F%2Fwww.youtube.com%2'
                            'Fwatch%3Fv%3DG5-KJgVsoUM&amp;key=87ca3314a9fa775b5c3a7726100694b0" style="border: 0; t'
                            'op: 0; left: 0; width: 100%; height: 100%; position: absolute;" allowfullscreen scroll'
                            'ing="no" allow="autoplay; encrypted-media"></iframe></div></div>',
                            "cache_age": 86400,
                        }
                    },
                }
            },
        }

        expected = (
            '<div class="embed-block"><div><div style="left: 0; width: 100%; height: 0; position: relative; padding-bot'
            'tom: 56.2493%;"><iframe src="//cdn.iframe.ly/api/iframe?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DG5'
            '-KJgVsoUM&amp;key=87ca3314a9fa775b5c3a7726100694b0" style="border: 0; top: 0; left: 0; width: 100%; height'
            ': 100%; position: absolute;" allowfullscreen scrolling="no" allow="autoplay; encrypted-media"></iframe></d'
            "iv></div></div>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_nested_inline_styles(self):
        """Check that nested inline styles are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": 'The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds". In the past,'
                    " variant spellings included Heelawes, Hielawes, Highlows, Hielows, and Hylaws.",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [
                        {"offset": 4, "length": 43, "style": "BOLD"},
                        {"offset": 21, "length": 5, "style": "UNDERLINE"},
                        {"offset": 32, "length": 3, "style": "ITALIC"},
                    ],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                }
            ],
            "entityMap": {},
        }

        expected = (
            "<p>The <b>name of Highlaws </b><b><u>comes</u></b><b> from </b><b><i>the</i></b><b> Old English</b> hēah-h"
            'lāw, meaning "high mounds". In the past, variant spellings included Heelawes, Hielawes, Highlows, Hielows,'
            " and Hylaws.</p>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_overlapping_inline(self):
        """Check that overlapping inline styles are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": 'The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds". In the past,'
                    " variant spellings included Heelawes, Hielawes, Highlows, Hielows, and Hylaws.",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [
                        {"offset": 0, "length": 66, "style": "BOLD"},
                        {"offset": 4, "length": 89, "style": "ITALIC"},
                        {"offset": 27, "length": 142, "style": "UNDERLINE"},
                        {"offset": 165, "length": 5, "style": "SUPERSCRIPT"},
                    ],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                }
            ],
            "entityMap": {},
        }

        expected = (
            "<p><b>The </b><b><i>name of Highlaws comes </i></b><b><i><u>from the Old English hēah-hlāw, meaning</u></i"
            '></b><i><u> "high mounds". In the past</u></i><u>, variant spellings included Heelawes, Hielawes, Highlows'
            ", Hielows, and </u><sup><u>Hyla</u></sup><sup>w</sup>s.</p>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_overlapping_inline_with_links(self):
        """Check that overlapping inline styles with links are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": 'The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds". In the past,'
                    " variant spellings included Heelawes, Hielawes, Highlows, Hielows, and Hylaws.",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [
                        {"offset": 12, "length": 14, "style": "BOLD"},
                        {"offset": 55, "length": 6, "style": "BOLD"},
                        {"offset": 48, "length": 18, "style": "UNDERLINE"},
                    ],
                    "entityRanges": [
                        {"offset": 21, "length": 10, "key": 0},
                        {"offset": 36, "length": 21, "key": 1},
                    ],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                }
            ],
            "entityMap": {
                "0": {
                    "type": "LINK",
                    "mutability": "MUTABLE",
                    "data": {"link": {"href": "https://en.wikipedia.org/wiki/Highlaws"}},
                },
                "1": {
                    "type": "LINK",
                    "mutability": "MUTABLE",
                    "data": {"link": {"href": "https://en.wikipedia.org/wiki/Highlaws"}},
                },
            },
        }

        expected = (
            '<p>The name of <b>Highlaws </b><a href="https://en.wikipedia.org/wiki/Highlaws"><b>comes</b> from</a> the '
            '<a href="https://en.wikipedia.org/wiki/Highlaws">Old English <u>hēah-hl</u><b><u>āw</u></b></a><b><u>, me<'
            '/u></b><u>aning</u> "high mounds". In the past, variant spellings included Heelawes, Hielawes, Highlows, H'
            "ielows, and Hylaws.</p>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_attachment(self):
        """Check that attachments are converted to HTML correctly"""

        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": 'The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".',
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [{"offset": 12, "length": 8, "key": 0}],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                }
            ],
            "entityMap": {
                "0": {
                    "type": "LINK",
                    "mutability": "MUTABLE",
                    "data": {"link": {"attachment": "5c9dd26d149f114c61d84db0"}},
                }
            },
        }

        expected = (
            '<p>The name of <a data-attachment="5c9dd26d149f114c61d84db0">Highlaws</a> comes from the Old English hēah-'
            'hlāw, meaning "high mounds".</p>'
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_lists(self):
        """Check that lists are correctly generated"""

        draftjs_data = self.blocks_with_text(
            [
                ["unordered-list-item", 0, "1"],
                ["unordered-list-item", 0, "2"],
                ["unordered-list-item", 1, "11"],
                ["unordered-list-item", 1, "22"],
                ["unordered-list-item", 1, "3"],
                ["unordered-list-item", 2, "4"],
                ["unordered-list-item", 2, "5"],
                ["unordered-list-item", 3, "6"],
                ["unordered-list-item", 3, "6.5"],
                ["unordered-list-item", 2, "x"],
                ["unordered-list-item", 1, "7"],
                ["unordered-list-item", 1, "33"],
                ["unordered-list-item", 0, "8"],
            ]
        )

        expected = (
            "<ul><li>1</li><li>2<ul><li>11</li><li>22</li><li>3<ul><li>4</li><li>5<ul><li>6</li><li>6.5</li></ul></li><"
            "li>x</li></ul></li><li>7</li><li>33</li></ul></li><li>8</li></ul>"
        )

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_lists_ending_abruptly(self):
        """Check that lists ending abruptly are correctly generated"""

        draftjs_data = self.blocks_with_text(
            [
                ["unordered-list-item", 0, "1"],
                ["unordered-list-item", 1, "2"],
                ["unordered-list-item", 2, "3"],
                ["unordered-list-item", 3, "4"],
                ["unstyled", 0, "abc"],
            ]
        )

        expected = "<ul><li>1<ul><li>2<ul><li>3<ul><li>4</li></ul></li></ul></li></ul></li></ul>\n<p>abc</p>"

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_annotation(self):
        """Check that annotations are correctly generated"""

        draftjs_data = {
            "entityMap": {},
            "blocks": [
                {
                    "inlineStyleRanges": [
                        {"length": 5, "style": "ANNOTATION-1", "offset": 6},
                        {"length": 5, "style": "ANNOTATION-2", "offset": 12},
                    ],
                    "data": {
                        "MULTIPLE_HIGHLIGHTS": {
                            "lastHighlightIds": {"ANNOTATION": 2},
                            "highlightsData": {
                                "ANNOTATION-1": {
                                    "data": {
                                        "email": "admin@admin.ro",
                                        "date": "2018-03-30T14:57:53.172Z",
                                        "msg": '{"blocks":[{"key":"ejm11","text":"Annotation 1","type":"unstyled","depth":'
                                        '0,"inlineStyleRanges":[],"entityRanges":[],"data":{}}],"entityMap":{}}',
                                        "author": "admin",
                                        "annotationType": "regular",
                                    },
                                    "type": "ANNOTATION",
                                },
                                "ANNOTATION-2": {
                                    "data": {
                                        "email": "admin@admin.ro",
                                        "date": "2018-03-30T14:58:20.876Z",
                                        "msg": '{"blocks":[{"key":"9i73f","text":"Annotation 2","type":"unstyled","depth":'
                                        '0,"inlineStyleRanges":[],"entityRanges":[],"data":{}},{"key":"d3vb3","text'
                                        '":"Line 2","type":"unstyled","depth":0,"inlineStyleRanges":[],"entityRange'
                                        's":[],"data":{}}],"entityMap":{}}',
                                        "author": "admin",
                                        "annotationType": "regular",
                                    },
                                    "type": "ANNOTATION",
                                },
                            },
                        },
                    },
                    "text": "lorem ipsum dolor",
                    "type": "unstyled",
                    "depth": 0,
                    "key": "2sso6",
                    "entityRanges": [],
                }
            ],
        }
        expected = '<p>lorem <span annotation-id="1">ipsum</span> <span annotation-id="2">dolor</span></p>'

        item = self.build_item(draftjs_data)
        editor = Editor3Content(item)
        html = editor.html
        self.assertEqual(html, expected)

    def test_embed_prepend(self):
        """Check that an embed block can be prepended"""
        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": 'The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".',
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                }
            ],
            "entityMap": {},
        }
        item = self.build_item(draftjs_data)
        body_editor = Editor3Content(item)
        embed_html = '<p class="some_class">some embedded HTML</p>'
        body_editor.prepend("embed", embed_html)
        body_editor.update_item()
        expected = (
            '<div class="embed-block"><p class="some_class">some embedded HTML</p></div>\n'
            '<p>The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".</p>'
        )
        self.assertEqual(item["body_html"], expected)

    def _modify_embed_content(self, data):
        data["html"] = data["html"].replace("some embedded HTML", "some modified embed")

    def test_embed_pre_process(self):
        """An embed can be pre-processed with a callback"""
        self.app.config["EMBED_PRE_PROCESS"] = [self._modify_embed_content]
        draftjs_data = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": 'The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".',
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                }
            ],
            "entityMap": {},
        }
        item = self.build_item(draftjs_data)
        body_editor = Editor3Content(item)
        embed_html = '<p class="some_class">some embedded HTML</p>'
        body_editor.prepend("embed", embed_html)
        body_editor.update_item()
        expected = (
            '<div class="embed-block"><p class="some_class">some modified embed</p></div>\n'
            '<p>The name of Highlaws comes from the Old English hēah-hlāw, meaning "high mounds".</p>'
        )
        self.assertEqual(item["body_html"], expected)

    def test_replace_text(self):
        draftjs_data = {
            "blocks": [
                {
                    "key": "foo",
                    "text": "first line text",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [
                        {"offset": 6, "length": 4, "style": "ITALIC"},
                    ],
                    "entityRanges": [],
                },
                {
                    "key": "bar",
                    "text": "second line",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [{"offset": 7, "length": 4, "key": 0}],
                },
            ],
            "entityMap": {
                "0": {
                    "type": "LINK",
                    "mutability": "MUTABLE",
                    "data": {"link": {"href": "http://example.com"}},
                }
            },
        }
        item_editor2 = {
            "body_html": '<p>first <i>line</i> text</p>\n<p>second <a href="http://example.com">line</a></p>'
        }
        item_editor3 = self.build_item(draftjs_data, "body_html")

        body_editor = Editor3Content(item_editor3, "body_html")
        body_editor.update_item()
        self.assertEqual(item_editor2["body_html"], item_editor3["body_html"])

        editor_utils.replace_text(item_editor2, "body_html", "first", "initial")
        editor_utils.replace_text(item_editor3, "body_html", "first", "initial")
        self.assertEqual(
            '<p>initial <i>line</i> text</p>\n<p>second <a href="http://example.com">line</a></p>',
            item_editor2["body_html"],
        )
        self.assertEqual(item_editor2["body_html"], item_editor3["body_html"])

        editor_utils.replace_text(item_editor2, "body_html", "text", "foo")
        editor_utils.replace_text(item_editor3, "body_html", "text", "foo")
        self.assertEqual(
            '<p>initial <i>line</i> foo</p>\n<p>second <a href="http://example.com">line</a></p>',
            item_editor2["body_html"],
        )
        self.assertEqual(item_editor2["body_html"], item_editor3["body_html"])

    def test_set_blocks(self):
        draftjs_data = {
            "blocks": [
                {
                    "key": "foo",
                    "text": "first line",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                },
                {
                    "key": "bar",
                    "text": "second line",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                },
            ],
            "entityMap": {},
        }

        item = self.build_item(draftjs_data)
        body_editor = Editor3Content(item)
        body_editor.set_blocks([block for block in body_editor.blocks if block.key == "bar"])
        self.assertEqual(1, len(body_editor.blocks))
        self.assertEqual("bar", body_editor.blocks[0].key)
        self.assertIn("MULTIPLE_HIGHLIGHTS", body_editor.blocks[0].data.get("data"))

        body_editor.set_blocks([])
        self.assertEqual(1, len(body_editor.blocks))
        self.assertIn("MULTIPLE_HIGHLIGHTS", body_editor.blocks[0].data.get("data"))

    def test_replace_text_no_html(self):
        item = {"headline": "foo bar"}
        editor_utils.replace_text(item, "headline", "bar", "baz", is_html=False)
        self.assertEqual("foo baz", item["headline"])

    def test_replace_text_inline_styles(self):
        item = {
            "body_html": "<h1>head</h1>\n<p>lorem <b>this is bold</b> and <b>bold</b> end</p>",
        }
        editor_utils.replace_text(item, "body_html", "bold", "UL")
        self.assertEqual("<h1>head</h1>\n<p>lorem <b>this is UL</b> and <b>UL</b> end</p>", item["body_html"])

    def test_replace_what_you_had_is_what_you_get(self):
        html = "\n".join(
            [
                "<h1>H1 foo</h1>",
                "<h2>H2 foo</h2>",
                "<h3>H3 foo</h3>",
                "<h4>H4 foo</h4>",
                "<p>P foo</p>",
                "<pre>PRE foo</pre>",
                "<blockquote>BLOCKQUOTE foo</blockquote>",
                '<!-- EMBED START Image {id: "editor_0"} -->',
                '<figure><img src="http://example.com" alt=""></figure>',
                '<!-- EMBED END Image {id: "editor_0"} -->',
                "<ul><li>LI foo</li><li>LI2 foo</li></ul>",
                "<ol><li>LI OL foo</li></ol>",
                (
                    "<table>"  # only parsing tables so far, no text replace in it
                    "<thead><tr><th><p>th foo</p></th></tr></thead>"
                    "<tbody><tr><td><p>td foo</p></td></tr></tbody>"
                    "</table>"
                ),
                '<p><a href="http://p.com" target="_blank">P</a> foo</p>',
                '<div class="embed-block"><script>foo</script></div>',
                '<div class="embed-block"><iframe src="http://iframe.com">foo</iframe></div>',
            ]
        )

        item = {
            "body_html": html,
            "associations": {
                "editor_0": {
                    "type": "picture",
                    "renditions": {
                        "original": {
                            "href": "http://example.com",
                        },
                    },
                },
            },
        }

        editor_utils.replace_text(item, "body_html", " foo", "")
        self.maxDiff = None
        self.assertEqual(html.replace(" foo", ""), item["body_html"])

        # test we keep draftjs state for next time
        item["body_html"] = "foo"
        editor_utils.replace_text(item, "body_html", " foo", "")
        self.assertEqual(html.replace(" foo", ""), item["body_html"])

    def test_filter_blocks(self):
        item = {
            "body_html": "".join(
                [
                    "<p>first line</p>",
                    "<p>second line</p>",
                ]
            ),
        }

        def block_filter(block):
            return "second" in block.text

        editor_utils.filter_blocks(item, "body_html", block_filter)
        self.assertEqual("<p>second line</p>", item["body_html"])

        item = {"body_html": ""}
        editor_utils.filter_blocks(item, "body_html", block_filter)
        self.assertEqual("", item["body_html"])

    def test_get_content_state_fields(self):
        """Fields with content states are detected correctly"""

        draftjs_data_headline = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": "headline test",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                }
            ],
            "entityMap": {},
        }
        draftjs_data_body_html = {
            "blocks": [
                {
                    "key": "fcbn3",
                    "text": "body_html test",
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                }
            ],
            "entityMap": {},
        }

        item = self.build_item(draftjs_data_headline, field="headline")
        self.update_item_field(item, draftjs_data_body_html, "body_html")
        found_fields = set(editor_utils.get_content_state_fields(item))
        self.assertEqual(found_fields, {"headline", "body_html"})

    def test_client_compatibility(self):
        client = (
            "<p>WestJet says it will operate its first Boeing 737 MAX flight on Jan. 21 since the aircraft was cleared to fly again in Canadian airspace.</p>\n"
            "<p><br></p>\n"
            "<p><br></p>\n"
            "<p><br></p>\n"
            "<p><b>This report by The Canadian Press was first published Month Date, 2021.</b></p>\n"
            "<p><b>Companies in this story: (TSX:TKTK)</b></p>"
        )
        field_state = json.loads(
            """
        {
    "entityMap": {},
    "blocks": [{
        "text": "WestJet says it will operate its first Boeing 737 MAX flight on Jan. 21 since the aircraft was cleared to fly again in Canadian airspace.",
        "data": {
            "MULTIPLE_HIGHLIGHTS": {}
        },
        "depth": 0,
        "key": "aft68",
        "inlineStyleRanges": [],
        "entityRanges": [],
        "type": "unstyled"
    }, {
        "text": "",
        "data": {},
        "depth": 0,
        "key": "fsdml",
        "inlineStyleRanges": [],
        "entityRanges": [],
        "type": "unstyled"
    }, {
        "text": "",
        "data": {},
        "depth": 0,
        "key": "cqlf1",
        "inlineStyleRanges": [],
        "entityRanges": [],
        "type": "unstyled"
    }, {
        "text": "",
        "data": {},
        "depth": 0,
        "key": "3ni9a",
        "inlineStyleRanges": [],
        "entityRanges": [],
        "type": "unstyled"
    }, {
        "text": "This report by The Canadian Press was first published Month Date, 2021.",
        "data": {},
        "depth": 0,
        "key": "bbduq",
        "inlineStyleRanges": [{
            "style": "BOLD",
            "length": 71,
            "offset": 0
        }],
        "entityRanges": [],
        "type": "unstyled"
    }, {
        "text": "Companies in this story: (TSX:TKTK)",
        "data": {},
        "depth": 0,
        "key": "alubr",
        "inlineStyleRanges": [{
            "style": "BOLD",
            "length": 35,
            "offset": 0
        }],
        "entityRanges": [],
        "type": "unstyled"
    }]
}
        """
        )
        item = self.build_item(field_state)
        body_editor = Editor3Content(item)
        body_editor.update_item()
        self.assertEqual(client, item["body_html"])
