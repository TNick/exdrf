import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Any, List

from attrs import define, field
from bs4 import Tag
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor

if TYPE_CHECKING:
    from exdrf_qt.controls.templ_viewer.html_to_docx.main import (
        HtmlToDocxConverter,
    )

logger = logging.getLogger(__name__)
TABLE_STRIPED_BG_COLOR_RGB = (0xF2, 0xF2, 0xF2)  # Light gray for striping


@define
class TableData:
    """Keeps track of the table data as we process the HTML.

    Attributes:
        html_grid: The grid for the docx table.
        html_rows: The rows from the HTML table.
        max_cols: The maximum number of columns across all rows.
        table_styles: The styles for the table.
        table_classes: The classes for the table.
        grid_r_idx: The current row index in the doc table.
        doc_table: The docx table object.
        num_logical_rows: The number of logical rows in the table.
    """

    cv: "HtmlToDocxConverter"
    html_grid: List[List[Tag | str | None]] = field(factory=list)
    html_rows: List[Tag] = field(factory=list)
    max_cols: int = field(default=0)
    table_styles: dict[str, Any] = field(factory=dict)
    table_classes: list[str] = field(factory=list)
    grid_r_idx: int = -1
    doc_table: Any = None
    num_logical_rows: int = 0

    def _collect_table_rows(self, table_element: Tag):
        """Collect all rows from a table element."""

        # Collect rows from the table header.
        thead = table_element.find("thead", recursive=False)
        if thead and isinstance(thead, Tag):
            for tag in thead.find_all("tr", recursive=False):
                if isinstance(tag, Tag):
                    self.html_rows.append(tag)

        # Collect rows from the table body.
        tbody_elements = table_element.find_all("tbody", recursive=False)
        if tbody_elements:
            for tbody in tbody_elements:
                if isinstance(tbody, Tag):
                    for tag in tbody.find_all("tr", recursive=False):
                        if isinstance(tag, Tag):
                            self.html_rows.append(tag)

        # Collect rows from within the table directly.
        for tag in table_element.find_all("tr", recursive=False):
            if isinstance(tag, Tag):
                self.html_rows.append(tag)

        # Collect rows from the table footer.
        tfoot = table_element.find("tfoot", recursive=False)
        if tfoot and isinstance(tfoot, Tag):
            for tag in tfoot.find_all("tr", recursive=False):
                if isinstance(tag, Tag):
                    self.html_rows.append(tag)

        logger.debug(
            "Collected %d HTML rows for the table.", len(self.html_rows)
        )

    def _handle_table_row(self, r_idx, tr_element_maybe_str) -> None:
        if not isinstance(tr_element_maybe_str, Tag):
            logger.debug(
                "Skipping non-<tr> element at index %d: %s",
                r_idx,
                str(tr_element_maybe_str)[:50],
            )
            return

        tr_element: Tag = tr_element_maybe_str

        # Check if the <tr> itself is hidden

        # This is the ID that we created ourselves in javascript.
        raw_tr_id = tr_element.get("data-docgen-id")
        tr_id_str: str | None = None
        if isinstance(raw_tr_id, list):
            if raw_tr_id:
                tr_id_str = str(raw_tr_id[0])
        elif isinstance(raw_tr_id, str):
            tr_id_str = raw_tr_id
        else:
            logger.warning(
                "Unexpected type for tr_id '%s': %s",
                raw_tr_id,
                type(raw_tr_id),
            )

        # Skip this entire row if the row is hidden.
        if tr_id_str:
            tr_element_data = self.cv.elements_map.get(tr_id_str)
            if tr_element_data and tr_element_data.get("is_hidden"):
                logger.debug(
                    "Skipping hidden <tr> element with ID %s", tr_id_str
                )
                return

        # Increment grid_r_idx and append row only for visible <tr>
        self.grid_r_idx += 1
        self.html_grid.append([])
        current_col_idx = 0
        if not isinstance(tr_element, Tag):
            # Should have been caught by first check
            logger.error(
                "Unexpected type for tr_element at index %d: %s",
                r_idx,
                type(tr_element),
            )
            return

        # Process each cell in the row.
        for td_th_element in tr_element.find_all(["td", "th"], recursive=False):
            if not isinstance(td_th_element, Tag):
                logger.warning(
                    "Skipping non-<td>/<th> element at index %d: %s",
                    r_idx,
                    str(td_th_element)[:50],
                )
                return

            # Move to the next available column in the grid
            while (
                len(self.html_grid[self.grid_r_idx]) > current_col_idx
                and self.html_grid[self.grid_r_idx][current_col_idx] is not None
            ):
                current_col_idx += 1
            logger.debug(
                "  Cell processing: grid_r_idx=%d, current_col_idx=%d",
                self.grid_r_idx,
                current_col_idx,
            )

            # Get colspan and rowspan attributes
            colspan = self.cv._get_attribute_as_int(td_th_element, "colspan", 1)
            rowspan = self.cv._get_attribute_as_int(td_th_element, "rowspan", 1)
            logger.debug(
                "    HTML Cell (%s): colspan=%d, rowspan=%d",
                str(td_th_element.name),
                colspan,
                rowspan,
            )

            # Process rowspan
            for i in range(rowspan):
                target_r_in_grid = self.grid_r_idx + i

                # Ensure rows up to the target row exist
                self.html_grid.extend(
                    [
                        []
                        for _ in range(
                            len(self.html_grid), target_r_in_grid + 1
                        )
                    ]
                )

                # Ensure enough columns in the target row
                while (
                    len(self.html_grid[target_r_in_grid])
                    < current_col_idx + colspan
                ):
                    self.html_grid[target_r_in_grid].append(None)

                # Assign cell or mark as SPAN
                for j in range(colspan):
                    cell_value = td_th_element if i == 0 and j == 0 else "SPAN"
                    self.html_grid[target_r_in_grid][
                        current_col_idx + j
                    ] = cell_value

            # Update column index for the next cell
            current_col_idx += colspan

            # Track maximum number of columns across all rows.
            self.max_cols = max(self.max_cols, current_col_idx)

    def _merged_cell(
        self,
        doc_cell,
        r_idx_grid_local: int,
        c_idx: int,
        colspan: int,
        rowspan: int,
    ) -> None:
        end_r_idx = min(
            r_idx_grid_local + rowspan - 1, self.num_logical_rows - 1
        )
        end_c_idx = min(c_idx + colspan - 1, self.max_cols - 1)
        if end_r_idx > r_idx_grid_local or end_c_idx > c_idx:
            try:
                doc_cell.merge(self.doc_table.cell(end_r_idx, end_c_idx))
                logger.debug(
                    "Merged cell at (grid_row=%d, col=%d) to "
                    "(grid_row=%d, col=%d)",
                    r_idx_grid_local,
                    c_idx,
                    end_r_idx,
                    end_c_idx,
                )
            except Exception as e:
                logger.warning(f"Cell merge failed: {e}")

    def _copy_borders(
        self,
        primary_tcBorders: Any,
        continued_tcPr: Any,
        r_idx_grid_local: int,
        c_idx: int,
        rowspan: int,
    ):
        """Copy borders from primary cell to continued cells"""
        for row_offset in range(1, rowspan):
            true_row_offset = r_idx_grid_local + row_offset
            if true_row_offset < self.num_logical_rows:
                continued_cell = self.doc_table.cell(true_row_offset, c_idx)
                continued_tcPr = continued_cell._tc.get_or_add_tcPr()

                logger.debug(
                    "    Setting w:vMerge from restart to "
                    "continue for cell (grid_row=%d, col=%d)",
                    r_idx_grid_local + row_offset,
                    c_idx,
                )

                # Set vMerge to "continue" for continued cells
                vmerge_elem = continued_tcPr.find(qn("w:vMerge"))
                if vmerge_elem is None:
                    vmerge_elem = OxmlElement("w:vMerge")
                    continued_tcPr.append(vmerge_elem)
                vmerge_elem.set(qn("w:val"), "continue")
                logger.debug(
                    "     Changed w:vMerge from restart to "
                    "continue for cell (grid_row=%d, col=%d)",
                    true_row_offset,
                    c_idx,
                )

                # Ensure all four sides (top, bottom, left, right) are
                # cloned. Remove any existing <w:tcBorders> child
                for old_borders in continued_tcPr.xpath("./w:tcBorders"):
                    continued_tcPr.remove(old_borders)

                # Create a new <w:tcBorders> and explicitly clone top,
                # bottom, left, right
                new_tc_borders_el = OxmlElement("w:tcBorders")
                # The four possible side tags, in Word’s expected order
                for side_tag in ("top", "bottom", "left", "right"):
                    # look for that side under primary_tcBorders
                    primary_side_el = primary_tcBorders.find(
                        qn(f"w:{side_tag}")
                    )
                    if primary_side_el is not None:
                        cloned_side_el = deepcopy(primary_side_el)
                        new_tc_borders_el.append(cloned_side_el)
                continued_tcPr.append(new_tc_borders_el)

    def _handle_cell(self, r_idx_grid_local: int, c_idx) -> None:
        html_cell_content = self.html_grid[r_idx_grid_local][c_idx]
        if html_cell_content is None or html_cell_content == "SPAN":
            return

        if not isinstance(html_cell_content, Tag):
            return

        html_cell_element: Tag = html_cell_content
        logger.debug(
            "Processing doc_cell at (grid_row=%d, col=%d) for " "HTML cell: %s",
            r_idx_grid_local,
            c_idx,
            str(html_cell_element)[:50],
        )
        doc_cell = self.doc_table.cell(r_idx_grid_local, c_idx)

        colspan = self.cv._get_attribute_as_int(html_cell_element, "colspan", 1)
        rowspan = self.cv._get_attribute_as_int(html_cell_element, "rowspan", 1)

        if rowspan > 1 or colspan > 1:
            self._merged_cell(
                doc_cell,
                r_idx_grid_local,
                c_idx,
                colspan,
                rowspan,
            )

        # Only remove the default <w:p> if we actually have content to add
        # i.e. if the HTML <td>/<th> has at least one child (text or tag)
        if html_cell_element is not None and list(html_cell_element.children):
            if doc_cell.paragraphs and doc_cell.paragraphs[0].text == "":
                p_element = doc_cell.paragraphs[0]._element
                p_element.getparent().remove(p_element)

        cell_styles, cell_classes = self.cv._parse_styles(html_cell_element)

        # Table striping and background color
        is_striped_table = "table-striped" in self.table_classes
        if is_striped_table and (r_idx_grid_local % 2 != 0):
            if not cell_styles.get("background-color"):
                shade_color = RGBColor(*TABLE_STRIPED_BG_COLOR_RGB)
                self.cv._set_cell_shading(doc_cell, str(shade_color))
        bg_color_str = cell_styles.get("background-color")
        if bg_color_str:
            self.cv._set_cell_shading(doc_cell, bg_color_str)

        # Apply borders to the primary cell
        self.cv._apply_cell_borders(
            doc_cell, cell_styles, cell_classes, self.table_classes
        )

        # Populate the cell with content from html_cell_element
        if html_cell_element and hasattr(html_cell_element, "children"):
            active_tags_for_cell_content = [html_cell_element]
            for child_node in html_cell_element.children:
                self.cv._process_block_element(
                    child_node, doc_cell, active_tags_for_cell_content
                )

        # Direct OXML tcBorders copy for continued cells in rowspan
        if rowspan > 1:
            primary_tcPr = doc_cell._tc.get_or_add_tcPr()
            primary_tcBorders = primary_tcPr.find(
                qn("w:tcBorders")
            )  # type: ignore[arg-type]
            logger.debug(
                "  Rowspan > 1 for cell at (grid_row=%d, col=%d). "
                "Primary tcBorders exists: %s",
                r_idx_grid_local,
                c_idx,
                primary_tcBorders is not None,
            )

            if primary_tcBorders is not None:
                self._copy_borders(
                    primary_tcBorders,
                    doc_cell._tc.get_or_add_tcPr(),
                    r_idx_grid_local,
                    c_idx,
                    rowspan,
                )

    def process(self, table_element: Tag, parent_docx_object):
        """Process a table element and convert it to a Docx table."""
        logger.debug(
            "--- Starting _handle_table for: %s ---", str(table_element)[:100]
        )

        # Get table classes
        self.table_styles, self.table_classes = self.cv._parse_styles(
            table_element
        )
        logger.debug(
            "Table styles: %s, Table classes: %s",
            self.table_styles,
            self.table_classes,
        )

        # Collect html rows.
        self._collect_table_rows(table_element)

        # Process each row.
        for r_idx, tr_element_maybe_str in enumerate(self.html_rows):
            self._handle_table_row(r_idx, tr_element_maybe_str)

        # Ensure the grid has enough columns.
        self.num_logical_rows = len(self.html_grid)
        for r_list in self.html_grid:
            while len(r_list) < self.max_cols:
                r_list.append(None)

        # If the table has 0 rows or 0 columns, skip it.
        if self.num_logical_rows == 0 or self.max_cols == 0:
            logger.warning(
                "Table has 0 rows or 0 columns after processing grid. "
                "Skipping table."
            )
            return

        self.doc_table = parent_docx_object.add_table(
            rows=self.num_logical_rows,
            cols=self.max_cols,
        )
        # Apply table-level styles like table-layout: fixed if needed (not
        # requested yet) doc_table.autofit = False doc_table.layout_type =
        # WD_TABLE_LAYOUT.FIXED

        for r_idx_grid_local in range(
            self.num_logical_rows
        ):  # Iterate using num_logical_rows (len of html_grid)
            for c_idx in range(self.max_cols):
                self._handle_cell(r_idx_grid_local, c_idx)

        logger.debug(
            "--- Finished _handle_table for: %s ---", str(table_element)[:100]
        )
