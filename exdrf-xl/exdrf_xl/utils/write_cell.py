from typing import (
    TYPE_CHECKING,
)

import openpyxl.cell._writer as cell_writer  # type: ignore[import]
import openpyxl.worksheet._writer as sheet_writer  # type: ignore[import]
from openpyxl.cell._writer import _set_attributes  # type: ignore[import]
from openpyxl.cell.rich_text import CellRichText  # type: ignore[import]
from openpyxl.compat import safe_string  # type: ignore[import]
from openpyxl.worksheet.formula import (  # type: ignore[import]
    ArrayFormula,
    DataTableFormula,
)
from openpyxl.xml.functions import XML_NS, Element  # type: ignore[import]

if TYPE_CHECKING:
    from openpyxl.cell import Cell
    from openpyxl.worksheet.worksheet import Worksheet


def lxml_write_cell_o(xf, worksheet: "Worksheet", cell: "Cell", styled=False):
    """Write a cell using lxml, preserving whitespace for strings.

    This is a lightly modified copy of openpyxl's cell writer, patched into
    openpyxl's writer module at import time. It allows writing cells that
    have both a formula and a precomputed value:

        - the cell datatype needs to be 'f'ormula
        - the internal value needs to be a tuple with two components:
            - the string formula prefixed by `=`.
            - the precomputed value.

    Args:
        xf: XML generator/writer.
        worksheet: Target worksheet instance.
        cell: Cell to serialize.
        styled: Whether to include style information for the cell.
    """
    value, attributes = _set_attributes(cell, styled)

    if value == "" or value is None:
        with xf.element("c", attributes):
            return

    if isinstance(value, tuple) and cell.data_type == "f":
        attributes["t"] = "str"

    with xf.element("c", attributes):
        if cell.data_type == "f":
            attrib = {}

            final_value = None

            if isinstance(value, ArrayFormula):
                attrib = dict(value)
                value = value.text

            elif isinstance(value, DataTableFormula):
                attrib = dict(value)
                value = None

            elif isinstance(value, tuple):
                assert len(value) == 2
                final_value = value[1]
                value = value[0]

            with xf.element("f", attrib):
                if value is not None and not attrib.get("t") == "dataTable":
                    assert value.startswith(
                        "="
                    ), "The formula type expects the first character to be `=`"
                    xf.write(value[1:])
                    value = final_value

        if cell.data_type == "s":
            if isinstance(value, CellRichText):
                el = value.to_tree()
                xf.write(el)
            else:
                with xf.element("is"):
                    if isinstance(value, str):
                        attrs = {}
                        if value != value.strip():
                            attrs["{%s}space" % XML_NS] = "preserve"
                        # lxml can't handle xml-ns
                        el = Element("t", attrs)
                        el.text = value
                        xf.write(el)

        else:
            with xf.element("v"):
                if value is not None:
                    xf.write(safe_string(value))


prev_cell_writer_write_cell = None
prev_cell_writer_lxml_write_cell = None
prev_worksheet_writer_wcell = None


def install_custom_lxml_writer():
    global prev_cell_writer_write_cell
    global prev_cell_writer_lxml_write_cell
    global prev_worksheet_writer_wcell

    if prev_cell_writer_write_cell is None:
        prev_cell_writer_write_cell = cell_writer.write_cell
        cell_writer.write_cell = lxml_write_cell_o  # type: ignore

    if prev_cell_writer_lxml_write_cell is None:
        prev_cell_writer_lxml_write_cell = cell_writer.lxml_write_cell
        cell_writer.lxml_write_cell = lxml_write_cell_o  # type: ignore

    if prev_worksheet_writer_wcell is None:
        prev_worksheet_writer_wcell = sheet_writer.write_cell  # type: ignore
        sheet_writer.write_cell = lxml_write_cell_o  # type: ignore


def uninstall_custom_lxml_writer():
    if prev_cell_writer_write_cell is not None:
        cell_writer.write_cell = prev_cell_writer_write_cell

    if prev_cell_writer_lxml_write_cell is not None:
        cell_writer.lxml_write_cell = prev_cell_writer_lxml_write_cell

    if prev_worksheet_writer_wcell is not None:
        sheet_writer.write_cell = prev_worksheet_writer_wcell  # type: ignore
