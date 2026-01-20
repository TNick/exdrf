import logging
from typing import TYPE_CHECKING, Generic, TypeVar

from exdrf_qt.controls.search_lines.base import BasicSearchLine
from exdrf_qt.utils.tlh import top_level_handler

if TYPE_CHECKING:
    from exdrf_qt.controls.search_lines.base import SearchData
    from exdrf_qt.models import QtModel


DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


class ModelSearchLine(BasicSearchLine, Generic[DBM]):
    """Search line that is specifically designed to search a model."""

    qt_model: "QtModel[DBM]"

    def __init__(
        self,
        model: "QtModel[DBM]",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.qt_model = model
        self.searchDataChanged.connect(self.apply_simple_search)

    @top_level_handler
    def on_show_settings(self) -> None:
        from exdrf_qt.controls.search_lines.model_settings import (
            ModelSearchSettings,
        )

        model_settings = ModelSearchSettings(self.qt_model, self)
        model_settings.create_search_mode_actions(self.search_data.search_type)
        model_settings.create_del_actions()
        model_settings.create_simple_filtering_actions()
        model_settings.run()

        if self.search_data.search_type != model_settings.search_mode:
            self.search_data.search_type = model_settings.search_mode
            self.searchDataChanged.emit(self.search_data)

    def apply_simple_search(self, data: "SearchData") -> None:
        if self.qt_model is None:
            return
        self.qt_model.apply_simple_search(data.term, data.search_type)
