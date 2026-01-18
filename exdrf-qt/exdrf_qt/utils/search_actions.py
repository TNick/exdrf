import logging
from typing import TYPE_CHECKING, Optional, Union

from exdrf.filter import SearchType
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QAction, QActionGroup

if TYPE_CHECKING:
    from exdrf_util.typedefs import HasTranslate


NAME_PREFIX = "search_type_"

logger = logging.getLogger(__name__)


def create_search_actions(
    ctx: "HasTranslate", current: "SearchType", parent: Optional[QObject] = None
) -> Union[QActionGroup, None]:
    """Create the actions for the deleted choice menu.

    Args:
        ctx: The context to use for translation.
        qt_model: The model to create the actions for.
        parent: The parent object for the actions.

    Returns:
        A list of QActions for selecting the deleted choice.
    """
    ac_group = QActionGroup(parent)

    ac_exact = QAction(
        ctx.t("cmn.search_type.exact", "Exact"),
        parent,
    )
    ac_exact.setObjectName(f"{NAME_PREFIX}{SearchType.EXACT.name}")
    ac_exact.setCheckable(True)
    ac_group.addAction(ac_exact)

    ac_simple = QAction(
        ctx.t("cmn.search_type.simple", "Simple"),
        parent,
    )
    ac_simple.setObjectName(f"{NAME_PREFIX}{SearchType.SIMPLE.name}")
    ac_simple.setCheckable(True)
    ac_group.addAction(ac_simple)

    ac_extended = QAction(
        ctx.t("cmn.search_type.extended", "Extended"),
        parent,
    )
    ac_extended.setObjectName(f"{NAME_PREFIX}{SearchType.EXTENDED.name}")
    ac_extended.setCheckable(True)
    ac_group.addAction(ac_extended)

    ac_pattern = QAction(
        ctx.t("cmn.search_type.pattern", "Pattern"),
        parent,
    )
    ac_pattern.setObjectName(f"{NAME_PREFIX}{SearchType.PATTERN.name}")
    ac_pattern.setCheckable(True)
    ac_group.addAction(ac_pattern)

    if current == SearchType.EXACT:
        ac_exact.setChecked(True)
    elif current == SearchType.SIMPLE:
        ac_simple.setChecked(True)
    elif current == SearchType.EXTENDED:
        ac_extended.setChecked(True)
    elif current == SearchType.PATTERN:
        ac_pattern.setChecked(True)
    else:
        logger.error("Invalid search type: %s", current)
        ac_simple.setChecked(True)

    return ac_group


def apply_search_action(
    ac_group: Union[QActionGroup, None],
) -> Union[SearchType, None]:
    """Apply the search type.

    Args:
        ac_group: The action group to apply the search type from.

    Returns:
        The search type.
    """
    if ac_group is None:
        return None

    active_ac = ac_group.checkedAction()
    if active_ac is None:
        logger.error("No active search type action")
        return None

    name = active_ac.objectName()
    if not name.startswith(NAME_PREFIX):
        logger.error("Invalid search type action: %s", name)
        return None

    name = name.removeprefix(NAME_PREFIX)
    if name == SearchType.EXACT.name:
        choice = SearchType.EXACT
    elif name == SearchType.SIMPLE.name:
        choice = SearchType.SIMPLE
    elif name == SearchType.EXTENDED.name:
        choice = SearchType.EXTENDED
    elif name == SearchType.PATTERN.name:
        choice = SearchType.PATTERN
    else:
        logger.error("Invalid search type action: %s", name)
        return None

    return choice
