from typing import TYPE_CHECKING, Optional, cast

from exdrf_qt.controls.task_runner.param_widget import ParamWidget
from exdrf_qt.controls.task_runner.ref_one_param import RefConfig
from exdrf_qt.field_ed.fed_sel_multi import DrfSelMultiEditor

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.task_runner import TaskRunner


class RefOneToManyParam(DrfSelMultiEditor, ParamWidget):
    """Widget for one-to-many reference parameters (multiple selection)."""

    def __init__(
        self,
        ctx: "QtContext",
        param: "TaskParameter",
        runner: "TaskRunner",
        parent: Optional[DrfSelMultiEditor] = None,
    ):
        config: RefConfig = cast(RefConfig, param.config)
        qt_model = config.get("qt_model")
        editor_class = config.get("editor_class")
        super_hack = config.get("super_hack")

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

        if param.value is not None:
            self.change_field_value(param.value)
        elif self.field_value is not None:
            param.value = self.field_value

        self.controlChanged.connect(self._on_value_changed)
        self.controlChanged.connect(self.runner._on_state_changed)

    def _on_value_changed(self):
        """Update param.value when field_value changes."""
        self.param.value = self.field_value

    def validate_param(self) -> Optional[str]:
        """Validate the current value."""
        error = super().validate_param()
        if error:
            return error
        # Reference lists are always valid if not None (or if nullable).
        return None
