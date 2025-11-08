from typing import TYPE_CHECKING

from attrs import define, field

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet


@define
class Range2Other:
    worksheet: "Worksheet"
    start_row: int
    start_col: int
    row_count: int
    col_count: int

    crt_row: int = field(default=1, init=False)
    crt_col: int = field(default=1, init=False)

    def validate_range(self):
        if self.start_row < 1:
            raise ValueError("start_row must be greater than 0")
        if self.start_col < 1:
            raise ValueError("start_col must be greater than 0")
        if self.row_count < 1:
            raise ValueError("row_count must be greater than 0")
        if self.col_count < 1:
            raise ValueError("col_count must be greater than 0")

    def valid_coords(self, r: int, c: int) -> bool:
        """Check if the coordinates are within the xl worksheet range.

        Args:
            r: The row number.
            c: The column number.

        Returns:
            True if the coordinates are within the range, False otherwise.
        """
        return (
            self.start_row <= r <= self.last_row
            and self.start_col <= c <= self.last_col
        )

    @property
    def last_row(self):
        """Get the last row number in the xl worksheet range."""
        return self.start_row + self.row_count - 1

    @property
    def last_col(self):
        """Get the last column number in the xl worksheet range."""
        return self.start_col + self.col_count - 1

    @property
    def rel_row(self):
        """Get the relative row number."""
        return self.crt_row - self.start_row

    @property
    def rel_col(self):
        """Get the relative column number."""
        return self.crt_col - self.start_col

    @property
    def xl_cell(self):
        """Retrieve the current cell from the worksheet."""
        return self.worksheet.cell(
            row=self.crt_row,
            column=self.crt_col,
        )

    @property
    def xl_cell_value(self):
        """Get the value of the current cell."""
        xl_cell = self.xl_cell
        return xl_cell.value if xl_cell.value is not None else ""

    @property
    def cell_key(self) -> str:
        """Get the key for the current cell."""
        return f"{self.crt_row}-{self.crt_col}"
