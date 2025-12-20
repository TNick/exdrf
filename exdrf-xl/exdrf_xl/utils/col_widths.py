import logging
import os

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)


def read_column_widths_from_existing_file(output_path):
    """Read column widths from existing Excel file.

    Args:
        output_path: Path to the existing Excel file.

    Returns:
        Dictionary mapping column names to widths.
    """
    column_widths = {}
    if not os.path.exists(output_path):
        return column_widths

    try:
        old_wb = load_workbook(output_path, read_only=True)
        if old_wb.sheetnames:
            try:
                ws = old_wb[old_wb.sheetnames[0]]
                # Read header row to get column names
                if ws.max_row > 0:
                    try:
                        header_row = ws[1]
                        # Check if header_row is not empty
                        if header_row:
                            for col_idx, cell in enumerate(header_row, start=1):
                                col_name = cell.value
                                if col_name:
                                    col_letter = get_column_letter(col_idx)
                                    col_dims = ws.column_dimensions
                                    width = col_dims[col_letter].width
                                    if width and width > 0:
                                        column_widths[str(col_name)] = width
                    except (IndexError, KeyError):
                        # Skip if header row can't be read
                        pass
            except Exception:
                # Skip if there's an error reading the sheet
                pass
        old_wb.close()
    except Exception as e:
        # If we can't read the old file, continue without widths
        logger.error("Error reading column widths from %s: %s", output_path, e)

    return column_widths
