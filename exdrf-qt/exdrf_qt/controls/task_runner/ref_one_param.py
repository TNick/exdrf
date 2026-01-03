from typing import TYPE_CHECKING, Any, Callable, Optional, TypedDict, cast

from PyQt5.QtWidgets import QWidget

from exdrf_qt.controls.task_runner.param_widget import (
    HasParamRunner,
    ParamWidget,
)
from exdrf_qt.field_ed.fed_sel_one import DrfSelOneEditor

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.models import QtModel


class RefConfig(TypedDict, total=False):
    """Configuration for reference parameters.

    Attributes:
        qt_model: The model for the selector.
        editor_class: Optional editor class for creating new records.
        super_hack: If you already have a class that inherits from
            DrfSelOneEditor you can pass its constructor here and
            it will be executed instead of the default constructor.
    """

    qt_model: "QtModel"
    editor_class: Optional[type]
    super_hack: Callable[..., Any]


class RefOneToOneParam(DrfSelOneEditor, ParamWidget):
    """Widget for one-to-one reference parameters (single selection).

    Attributes:
        ctx: The Qt context.
        runner: The task runner that contains this widget.
        param: The task parameter this widget represents.
    """

    ctx: "QtContext"
    runner: "HasParamRunner"
    param: "TaskParameter"

    def __init__(
        self,
        ctx: "QtContext",
        param: "TaskParameter",
        runner: "HasParamRunner",
        parent: Optional[QWidget] = None,
    ):
        """Initialize the one-to-one reference parameter widget.

        Args:
            ctx: The Qt context.
            param: The task parameter this widget represents.
            runner: The task runner that contains this widget.
            parent: The parent widget.
        """
        config: RefConfig = cast(RefConfig, param.config)
        qt_model = config.get("qt_model")
        editor_class = config.get("editor_class")
        super_hack = config.get("super_hack")

        # Build arguments for the parent constructor.
        args = {
            "nullable": param.nullable,
            "description": param.description,
            "parent": parent,
            "name": param.name,
            "ctx": ctx,
        }
        if qt_model is not None:
            args["qt_model"] = qt_model
        if editor_class is not None:
            args["editor_class"] = editor_class

        # Initialize the parent class.
        if super_hack:
            super_hack(self, **args)
        else:
            if not qt_model:
                raise ValueError("qt_model must be specified in config")

            super().__init__(
                ctx=ctx,
                qt_model=qt_model,
                editor_class=editor_class,
                parent=parent,
            )
        self.runner = runner
        self.param = param

        # Set initial value if provided.
        if param.value is not None:
            self.change_field_value(param.value)
        elif self.field_value is not None:
            param.value = self.field_value

        # Connect signals.
        self.controlChanged.connect(self._on_value_changed)
        self.controlChanged.connect(self.runner._on_state_changed)

    def _on_value_changed(self):
        """Update param.value when field_value changes."""
        self.param.value = self.field_value
