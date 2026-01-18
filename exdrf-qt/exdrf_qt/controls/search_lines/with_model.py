import logging
from typing import TYPE_CHECKING, Generic, Optional, TypeVar

from exdrf_qt.controls.search_lines.base import BasicSearchLine

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget

    from exdrf_qt.context import QtContext
    from exdrf_qt.models import QtModel


DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


class ModelSearchLine(BasicSearchLine, Generic[DBM]):
    """Search line that is specifically designed to search a model."""

    def __init__(
        self,
        ctx: "QtContext",
        model: "QtModel[DBM]",
        parent: Optional["QWidget"] = None,
    ) -> None:
        super().__init__(ctx, parent)
        self.model = model
