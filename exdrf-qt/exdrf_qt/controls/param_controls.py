"""Shared helpers for building parameter controls and pages.

The UI for task parameters is needed in multiple widgets (task runner, checks
manager). This module provides a mixin with small, focused ``create_*`` methods
and a type-dispatch function, following the style of ``TaskRunner``.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Optional, cast

from exdrf.constants import (
    FIELD_TYPE_BLOB,
    FIELD_TYPE_BOOL,
    FIELD_TYPE_DATE,
    FIELD_TYPE_DT,
    FIELD_TYPE_DURATION,
    FIELD_TYPE_ENUM,
    FIELD_TYPE_FLOAT,
    FIELD_TYPE_FLOAT_LIST,
    FIELD_TYPE_FORMATTED,
    FIELD_TYPE_INT_LIST,
    FIELD_TYPE_INTEGER,
    FIELD_TYPE_REF_ONE_TO_MANY,
    FIELD_TYPE_REF_ONE_TO_ONE,
    FIELD_TYPE_STRING,
    FIELD_TYPE_STRING_LIST,
    FIELD_TYPE_TIME,
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFormLayout, QLabel, QWidget

if TYPE_CHECKING:
    from exdrf_util.task import TaskParameter

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.task_runner.param_widget import HasParamRunner


class TaskParameterControlsMixin:
    """Mixin that provides UI controls for ``TaskParameter``.

    The mixin expects the using class to:
    - expose ``ctx`` (Qt context) attribute
    - implement translation method ``t`` (typically via ``QtUseContext``)

    Attributes:
        ctx: The Qt context.
    """

    ctx: "QtContext"

    def _on_state_changed(self) -> None:
        """Signal that the current input state has changed.

        Parameter widgets connect to this callback on the runner. Widgets that
        use this mixin should implement the behavior, but a no-op is acceptable
        for cases where no validation state is needed.
        """

    def _register_parameter_widget(
        self, param: "TaskParameter", widget: QWidget
    ) -> None:
        """Hook for subclasses to track created parameter widgets.

        Args:
            param: The parameter for which the widget was created.
            widget: The created widget.
        """
        del param
        del widget

    def create_bool_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a boolean parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.bool_param import BoolParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return BoolParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_string_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a string parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.str_param import StrParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        widget = StrParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )
        return widget.get_widget()

    def create_integer_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for an integer parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.int_param import IntParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        widget = IntParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )
        return widget.get_widget()

    def create_float_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a float parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.float_param import FloatParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        widget = FloatParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )
        return widget.get_widget()

    def create_date_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a date parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.date_param import DateParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return DateParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_dt_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a datetime parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.datetime_param import DateTimeParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return DateTimeParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_time_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a time parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.time_param import TimeParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return TimeParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_duration_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a duration parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.duration_param import DurationParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return DurationParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_enum_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for an enum parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.enum_param import EnumParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return EnumParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_formatted_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a formatted parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.formatted_param import FormattedParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return FormattedParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_blob_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a blob parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.blob_param import BlobParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return BlobParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_string_list_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a string list parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.str_list_param import StrListParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return StrListParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_int_list_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for an integer list parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.int_list_param import IntListParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return IntListParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_float_list_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a float list parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.float_list_param import (
            FloatListParam,
        )

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return FloatListParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_ref_one_to_one_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a one-to-one reference parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.ref_one_param import RefOneToOneParam

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return RefOneToOneParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_ref_one_to_many_control(self, param: "TaskParameter") -> QWidget:
        """Create a control for a one-to-many reference parameter.

        Args:
            param: The parameter definition.

        Returns:
            The created widget.
        """
        from exdrf_qt.controls.task_runner.ref_many_param import (
            RefOneToManyParam,
        )

        runner = cast("HasParamRunner", self)
        parent = cast(QWidget, self)
        return RefOneToManyParam(
            ctx=self.ctx,
            param=param,
            runner=runner,
            parent=parent,
        )

    def create_control_for_parameter(
        self, param: "TaskParameter", parent: Optional[QWidget] = None
    ) -> QWidget:
        """Create a control for a parameter.

        Args:
            param: The parameter definition.
            parent: Optional parent widget (unused for most controls).

        Returns:
            The created widget.
        """
        del parent

        if param.type_name == FIELD_TYPE_BOOL:
            w = self.create_bool_control(param)
        elif param.type_name == FIELD_TYPE_STRING:
            w = self.create_string_control(param)
        elif param.type_name == FIELD_TYPE_INTEGER:
            w = self.create_integer_control(param)
        elif param.type_name == FIELD_TYPE_FLOAT:
            w = self.create_float_control(param)
        elif param.type_name == FIELD_TYPE_DATE:
            w = self.create_date_control(param)
        elif param.type_name == FIELD_TYPE_DT:
            w = self.create_dt_control(param)
        elif param.type_name == FIELD_TYPE_TIME:
            w = self.create_time_control(param)
        elif param.type_name == FIELD_TYPE_DURATION:
            w = self.create_duration_control(param)
        elif param.type_name == FIELD_TYPE_ENUM:
            w = self.create_enum_control(param)
        elif param.type_name == FIELD_TYPE_FORMATTED:
            w = self.create_formatted_control(param)
        elif param.type_name == FIELD_TYPE_BLOB:
            w = self.create_blob_control(param)
        elif param.type_name == FIELD_TYPE_REF_ONE_TO_MANY:
            w = self.create_ref_one_to_many_control(param)
        elif param.type_name == FIELD_TYPE_REF_ONE_TO_ONE:
            w = self.create_ref_one_to_one_control(param)
        elif param.type_name == FIELD_TYPE_STRING_LIST:
            w = self.create_string_list_control(param)
        elif param.type_name == FIELD_TYPE_INT_LIST:
            w = self.create_int_list_control(param)
        elif param.type_name == FIELD_TYPE_FLOAT_LIST:
            w = self.create_float_list_control(param)
        else:
            raise ValueError(f"Invalid type: {param.type_name}")

        self._register_parameter_widget(param, w)
        return w

    def create_parameters_page(
        self,
        controls: "OrderedDict[str, TaskParameter]",
        parent: Optional[QWidget] = None,
    ) -> QWidget:
        """Create a QWidget with a QFormLayout for a set of parameters.

        Args:
            controls: Parameters to show.
            parent: Optional parent widget (defaults to ``self``).

        Returns:
            The created page widget.
        """
        if parent is None:
            parent = cast(QWidget, self)

        # Create the page and its layout.
        page = QWidget(parent)
        lay = QFormLayout()
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)
        page.setLayout(lay)

        label_font = None

        # Populate the form.
        for parameter in controls.values():
            lay.addRow(
                parameter.title,
                self.create_control_for_parameter(parameter),
            )

            if parameter.description:
                lbl = QLabel(parameter.description, parent)
                lbl.setTextInteractionFlags(
                    cast(
                        "Qt.TextInteractionFlags",
                        Qt.TextInteractionFlag.TextSelectableByMouse
                        | Qt.TextInteractionFlag.TextSelectableByKeyboard,
                    )
                )
                lbl.setWordWrap(True)
                if label_font is None:
                    label_font = lbl.font()
                    label_font.setItalic(True)
                lbl.setFont(label_font)
                lbl.setContentsMargins(0, 0, 0, 2)
                lay.addRow(lbl)

        return page
