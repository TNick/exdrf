import logging
from typing import TYPE_CHECKING, Optional, Union

from exdrf_al.utils import DelChoice
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QAction, QActionGroup

if TYPE_CHECKING:
    from exdrf_util.typedefs import HasTranslate

    from exdrf_qt.models.model import QtModel


NAME_PREFIX = "del_choice_"

logger = logging.getLogger(__name__)


def create_del_actions(
    ctx: "HasTranslate", qt_model: "QtModel", parent: Optional[QObject] = None
) -> Union[QActionGroup, None]:
    """Create the actions for the deleted choice menu.

    Args:
        ctx: The context to use for translation.
        qt_model: The model to create the actions for.
        parent: The parent object for the actions.

    Returns:
        A list of QActions for selecting the deleted choice.
    """
    if not qt_model.has_soft_delete_field:
        return None

    del_choice = qt_model.del_choice

    ac_group = QActionGroup(parent)

    ac_not_deleted = QAction(
        ctx.t("cmn.del_choice.not_deleted", "Not Deleted"),
        parent,
    )
    ac_not_deleted.setObjectName(f"{NAME_PREFIX}{DelChoice.ACTIVE.name}")
    ac_not_deleted.setCheckable(True)
    ac_not_deleted.setChecked(del_choice == DelChoice.ACTIVE)
    ac_group.addAction(ac_not_deleted)

    ac_deleted = QAction(
        ctx.t("cmn.del_choice.deleted", "Deleted"),
        parent,
    )
    ac_deleted.setObjectName(f"{NAME_PREFIX}{DelChoice.DELETED.name}")
    ac_deleted.setCheckable(True)
    ac_deleted.setChecked(del_choice == DelChoice.DELETED)
    ac_group.addAction(ac_deleted)

    ac_all = QAction(
        ctx.t("cmn.del_choice.all", "All"),
        parent,
    )
    ac_all.setObjectName(f"{NAME_PREFIX}{DelChoice.ALL.name}")
    ac_all.setCheckable(True)
    ac_all.setChecked(del_choice == DelChoice.ALL)
    ac_group.addAction(ac_all)
    return ac_group


def apply_del_action(
    ac_group: Union[QActionGroup, None], qt_model: "QtModel"
) -> Union[DelChoice, None]:
    """Apply the deleted choice to the model.

    You can use this function with the result of calling menu.exec_() to apply
    the deleted choice if the user selected an action created by
    create_del_actions().

    If the action is not one of the actions created by create_del_actions(),
    None is returned and the model is not changed.

    Args:
        action: The action to apply.
        qt_model: The model to apply the deleted choice to.

    Returns:
        The deleted/non-deleted/all choice.
    """
    if ac_group is None:
        return None

    active_ac = ac_group.checkedAction()
    if active_ac is None:
        return None

    name = active_ac.objectName()
    if not name.startswith(NAME_PREFIX):
        return None
    name = name.removeprefix(NAME_PREFIX)
    if name == DelChoice.ACTIVE.name:
        choice = DelChoice.ACTIVE
    elif name == DelChoice.DELETED.name:
        choice = DelChoice.DELETED
    elif name == DelChoice.ALL.name:
        choice = DelChoice.ALL
    else:
        logger.error("Invalid del choice action: %s", name)
        return None
    qt_model.del_choice = choice
    return choice
