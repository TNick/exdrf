import logging
from typing import TYPE_CHECKING, List, Optional

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QAction

if TYPE_CHECKING:
    from exdrf_util.typedefs import HasTranslate

    from exdrf_qt.models.model import QtModel


NAME_PREFIX = "spl_src_flt_act"

logger = logging.getLogger(__name__)


def create_simple_filtering_actions(
    ctx: "HasTranslate", qt_model: "QtModel", parent: Optional[QObject] = None
) -> List["QAction"]:
    """Create the simple filtering actions for the given model.

    Args:
        ctx: The context to use for translation.
        qt_model: The model to create the actions for.
        parent: The parent object for the actions.

    Returns:
        A list of QActions for simple filtering.
    """
    actions = []
    for i, (enabled, field) in enumerate(qt_model.simple_search_field_states):
        action = QAction(
            ctx.t(
                f"db.{qt_model.name}.{field.name}",
                " ".join(field.name.split("_")).capitalize(),
            ).capitalize(),
            parent=parent,
        )
        action.setCheckable(True)
        action.setChecked(enabled)
        action.setObjectName(f"{NAME_PREFIX}-{qt_model.name}-{field.name}")
        action.setData(i)
        actions.append(action)
    return actions


def apply_simple_filtering_action(
    actions: List[QAction], qt_model: "QtModel"
) -> List[bool]:
    """Apply the simple filtering action to the given model.

    Args:
        action: The action to apply.
        qt_model: The model to apply the simple filtering action to.

    Returns:
        The index of the field that was filtered.
    """
    result = [True for _ in actions]
    if len(result) != len(qt_model.simple_search_fields):
        logger.error(
            "The number of results must match the number of fields: %s != %s",
            len(result),
            len(qt_model.simple_search_fields),
        )
        return [True for _ in qt_model.simple_search_fields]

    for action in actions:
        name = action.objectName()
        if not name.startswith(NAME_PREFIX):
            logger.error(
                "Invalid object name for simple filtering action %s", name
            )
            continue
        i = action.data()
        if i is None or not isinstance(i, int):
            logger.error(
                "Invalid data for simple filtering action %s: %s", name, i
            )
            continue

        if 0 <= i < len(result):
            result[i] = action.isChecked()
        else:
            logger.error(
                "Invalid index for simple filtering action %s: %s", name, i
            )

    qt_model.set_simple_search_field_states(result)
    return result
