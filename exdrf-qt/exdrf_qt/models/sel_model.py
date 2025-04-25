from typing import TYPE_CHECKING, List, cast

from exdrf.constants import RecIdType
from sqlalchemy import func, select

from exdrf_qt.models.model import QtModel

if TYPE_CHECKING:
    from exdrf_qt.models.record import QtRecord  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

from sqlalchemy import or_


class QtSelectModel(QtModel):
    """A model that allows for selection of items.

    The selected items are showed to the top of the list,
    with a distinct item shown that separates the two
    sets (selected and unselected).
    """

    selected: List["QtRecord"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected = []

    @property
    def selected_ids(self) -> List[RecIdType]:
        """Return the IDs of the selected items."""
        return [item.db_id for item in self.selected if item.db_id is not None]

    def reset_model(self) -> None:
        self.beginResetModel()
        self.cache = []
        self.selected = []
        self.total_count = -1
        self.loaded_count = -1
        self.recalculate_total_count()
        self.endResetModel()

    def recalculate_total_count(self) -> int:
        with self.ctx.same_session() as session:

            selected_ids = self.selected_ids
            if selected_ids:
                count_query = (
                    select(func.count())
                    .select_from(self.db_model)
                    .where(
                        or_(
                            self.get_primary_columns().in_(
                                select(self.get_primary_columns()).select_from(
                                    self.filtered_selection.subquery()
                                )
                            ),
                            self.get_id_filter(selected_ids),
                        )
                    )
                )
                extra_item = 1  # for the divider
            else:
                count_query = select(func.count()).select_from(
                    self.filtered_selection.subquery()
                )
                extra_item = 0  # for the divider

            count = cast(int, session.scalar(count_query))
            self.total_count = count + extra_item
            return count

    @property
    def filtered_selection(self) -> "Select":
        """Return the selection with filtering applied.

        The function starts from the `root_selection` and asks all filters
        to apply themselves but it does not change the internal `selection`
        attribute.

        If an exception occurs, the function logs the error and returns the
        `selection` attribute.
        """
        selected_ids = self.selected_ids
        up_sel = super().filtered_selection
        if selected_ids:
            pass
        else:
            return up_sel
