import logging
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from attrs import define, field
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMenu, QMenuBar

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.plugins import exdrf_qt_pm, hook_spec
from exdrf_qt.utils.plugins import safe_hook_call

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.controls.command_palette.line_edit import (  # noqa: F401
        CommandPalette,
    )

logger = logging.getLogger(__name__)
VERBOSE = 1


@define
class PlacementRule:
    """Describes the way a menu or action should be placed in the menu
    structure.

    Attributes:
        ref: the key of the menu or action to place the menu or action
            before or after.
        before: if True the menu or action will be placed before the reference.
            If False the menu or action will be placed after the reference.
    """

    ref: str = field(repr=False)
    before: bool = field(default=False, repr=False)


@define
class DefBase:
    """Describes the way a menu should be build.

    Attributes:
        key: a unique string that identifies the menu or action.
            Should be unique across all menus and actions.
        label: the label of the menu or action.
        parent: the path to the parent menu or action. If empty the
            menu or action will be placed in the root.
        rules: placement rules that determine where this menu or action
            should be placed relative to other menus or actions.
        icon: optional icon to display for the menu or action.
    """

    key: str
    label: str = field(repr=False)
    parent: Tuple[str, ...] = field(repr=False)
    rules: Tuple[PlacementRule, ...] = field(factory=tuple, repr=False)
    icon: Optional[QIcon] = field(default=None, repr=False)


@define
class ActionDef(DefBase):
    """Describes the way an action should be build.

    Attributes:
        callback: The function to call when the action is triggered.
        description: Optional description text for the action.
        no_menu: If True this action should not be added to any menu, but it
            can still be available via other mechanisms (e.g. command palette).
        no_command_palette: If True this action should not be available in the
            command palette.
    """

    callback: Callable[[], None] = field(
        factory=lambda: lambda: None, repr=False
    )
    description: Optional[str] = field(default=None, repr=False)
    no_menu: bool = field(default=False, repr=False)
    no_command_palette: bool = field(default=False, repr=False)
    tags: List[str] = field(factory=list, repr=False)


@define
class MenuDef(DefBase):
    """Describes the way a menu should be build.

    This class inherits all attributes from DefBase and does not add any
    additional attributes.
    """


@define
class NewMenus(QtUseContext):
    """Manages creating menus from multiple sources.

    The class registers a hook that you have to implement and which should
    create the definitions for menus and actions. When the host window is
    creates this hook is interrogated and a list of definitions is compiled
    from all the providers. The list is then sorted according to the placement
    rules and the menus and actions are created. Each menu or action is then
    available in the `created` attribute under same key as the definition.

    Attributes:
        defs: Dictionary mapping menu/action keys to their definitions.
        created: Dictionary mapping menu/action keys to the created QMenu or
            QAction instances.
        ctx: The Qt context for accessing translations, icons, and database
            connections.
    """

    defs: Dict["str", "DefBase"] = field(factory=dict, repr=False)
    created: Dict["str", Union["QMenu", "QAction"]] = field(
        factory=dict, repr=False
    )

    @property
    def ctx(self) -> "QtContext":
        raise NotImplementedError

    @ctx.setter
    def ctx(self, ctx: "QtContext"):  # type: ignore
        raise NotImplementedError

    @hook_spec
    def create_extra_main_menu_defs(self, ctx: "QtContext") -> List["DefBase"]:
        """Hook definition for creating extra menus and actions.

        Implement this hook to create menus and actions in the main menu.

        Args:
            ctx: The Qt context for accessing translations, icons, and database
                connections.

        Returns:
            List[DefBase]: A list of definitions for menus and actions.
        """
        raise NotImplementedError

    def pre_create(
        self,
        ctx: "QtContext",
        top_parent: Union["QMenu", "QMenuBar"],
        default_menu: "QMenu",
        existing: Dict["str", "QMenu"],
    ):
        """Called before the menus are created.

        Args:
            ctx: The Qt context for accessing translations, icons, and database
                connections.
            top_parent: Menus that have no parent will be added to this menu.
            default_menu: The menu where actions without a parent will be added.
            existing: A dictionary of existing menus to use, keyed by menu key.
        """

    def post_create(
        self,
        ctx: "QtContext",
        top_parent: Union["QMenu", "QMenuBar"],
        default_menu: "QMenu",
        existing: Dict["str", "QMenu"],
    ):
        """Called after the menus are created.

        Args:
            ctx: The Qt context for accessing translations, icons, and database
                connections.
            top_parent: Menus that have no parent will be added to this menu.
            default_menu: The menu where actions without a parent will be added.
            existing: A dictionary of existing menus to use, keyed by menu key.
        """

    def collect_and_create(
        self,
        ctx: "QtContext",
        top_parent: Union["QMenu", "QMenuBar"],
        default_menu: "QMenu",
        existing: Dict["str", "QMenu"],
    ):
        """Collects the definitions from the hook and sorts them according to
        the placement rules.

        Args:
            ctx: The Qt context for accessing translations, icons, and database
                connections.
            top_parent: Menus that have no parent will be added to this menu.
            default_menu: The menu where actions without a parent will be added.
            existing: A dictionary of existing menus to use, keyed by menu key.
        """
        logger.log(VERBOSE, "collect_and_create menus starts")
        self.pre_create(ctx, top_parent, default_menu, existing)

        # Populate the existing menus.
        for key, menu in existing.items():
            self.created[key] = menu

        # Ask plugins to create the definitions.
        result_map, error_map = safe_hook_call(
            exdrf_qt_pm.hook.create_extra_main_menu_defs, ctx=ctx
        )

        # Log errors.
        for plugin_name, error in error_map.items():
            logger.error(
                "Error in in %s hook of the %s plugin: %s",
                exdrf_qt_pm.hook.create_extra_main_menu_defs.name,
                plugin_name,
                error,
            )
        logger.log(VERBOSE, "result_map has %d items", len(result_map))

        # Add the definitions to the class.
        for plugin_name, defs in result_map.items():
            for iter_def in defs:
                if iter_def.key in self.defs:
                    logger.warning(
                        "Duplicate definition key %s in %s plugin",
                        iter_def.key,
                        plugin_name,
                    )
                self.defs[iter_def.key] = iter_def

        # Separate menus and actions for two-pass creation
        menu_defs = [
            def_item
            for def_item in self.defs.values()
            if isinstance(def_item, MenuDef)
        ]
        action_defs = [
            def_item
            for def_item in self.defs.values()
            if isinstance(def_item, ActionDef)
        ]
        logger.log(
            VERBOSE,
            "%d menu definitions, %d action definitions",
            len(menu_defs),
            len(action_defs),
        )

        # First pass: create menus
        self._create_menus(menu_defs, top_parent, default_menu)

        # Second pass: create actions
        self._create_actions(action_defs, top_parent, default_menu)

        self.post_create(ctx, top_parent, default_menu, existing)
        logger.log(VERBOSE, "collect_and_create done")

    def _create_menus(
        self,
        menu_defs: List["MenuDef"],
        top_parent: Union["QMenu", "QMenuBar"],
        default_menu: "QMenu",
    ):
        """Create menus from definitions.

        Args:
            menu_defs: List of menu definitions to create.
            top_parent: The top-level parent for menus without parents.
            default_menu: Default menu for menus without parents.
        """
        # Sort menus by their placement rules
        sorted_menus = cast("List[MenuDef]", self._sort_definitions(menu_defs))

        for menu_def in sorted_menus:
            if menu_def.key in self.created:
                continue  # Skip if already exists

            # Find or create parent menu
            parent_menu = self._find_or_create_parent_menu(
                menu_def.parent, top_parent, default_menu
            )

            # Create the menu
            new_menu = QMenu(menu_def.label, parent_menu)
            new_menu.setObjectName(menu_def.key)
            self.created[menu_def.key] = new_menu

            # Add to parent
            parent_menu.addMenu(new_menu)

    def _create_actions(
        self,
        action_defs: List["ActionDef"],
        top_parent: Union["QMenu", "QMenuBar"],
        default_menu: "QMenu",
    ):
        """Create actions from definitions.

        Args:
            action_defs: List of action definitions to create.
            top_parent: The top-level parent for actions without parents.
            default_menu: Default menu for actions without parents.
        """
        # Sort actions by their placement rules
        sorted_actions = cast(
            "List[ActionDef]", self._sort_definitions(action_defs)
        )

        for action_def in sorted_actions:
            # Skip no_menu actions - they are not created as QActions,
            # only stored in defs for command palette access.
            if action_def.no_menu:
                continue

            if action_def.key in self.created:
                # Skip if already exists.
                continue

            # Find or create parent menu
            if action_def.parent:
                parent_menu = self._find_or_create_parent_menu(
                    action_def.parent, top_parent, default_menu
                )
            else:
                parent_menu = default_menu

            # The first line of the description is the status bar message.
            status_bar_message = ""
            if action_def.description:
                status_bar_message = action_def.description.split("\n")[0]
            else:
                status_bar_message = action_def.label

            # Create the action
            new_action = QAction(action_def.label, parent_menu)
            new_action.setObjectName(action_def.key)
            new_action.setStatusTip(status_bar_message)
            new_action.triggered.connect(cast(ActionDef, action_def).callback)
            self.created[action_def.key] = new_action

            # Add to parent menu
            parent_menu.addAction(new_action)

    def _find_or_create_parent_menu(
        self,
        parent_path: Tuple[str, ...],
        top_parent: Union["QMenu", "QMenuBar"],
        default_menu: "QMenu",
    ) -> Union["QMenu", "QMenuBar"]:
        """Find or create parent menu based on path.

        Args:
            parent_path: Path to the parent menu.
            top_parent: The top-level parent.
            default_menu: Default menu if no parent specified.

        Returns:
            The parent menu or menu bar.
        """
        if not parent_path:
            return (
                top_parent if isinstance(top_parent, QMenuBar) else default_menu
            )

        current_parent = top_parent
        missing_menus = []

        for menu_key in parent_path:
            if menu_key in self.created:
                current_parent = cast(QMenu, self.created[menu_key])
                if not isinstance(current_parent, QMenu):
                    logger.warning(
                        "Parent %s is not a menu, using default menu", menu_key
                    )
                    current_parent = default_menu
            else:
                # Create missing menu
                missing_menu = QMenu(menu_key, current_parent)
                self.created[menu_key] = missing_menu
                current_parent = missing_menu
                missing_menus.append(menu_key)

                # Add to parent
                if isinstance(current_parent, QMenuBar):
                    current_parent.addMenu(missing_menu)
                else:
                    current_parent.addMenu(missing_menu)

        # Log warnings for missing menus
        for menu_key in missing_menus:
            logger.warning("Created missing parent menu: %s", menu_key)

        return current_parent

    def _sort_definitions(
        self, definitions: Sequence["DefBase"]
    ) -> List["DefBase"]:
        """Sort definitions based on placement rules.

        Args:
            definitions: List of definitions to sort.

        Returns:
            Sorted list of definitions.
        """
        # Create a mapping of key to definition for quick lookup
        def_map = {def_item.key: def_item for def_item in definitions}

        # Build dependency graph
        dependencies: Dict[str, List[str]] = {}
        for def_item in definitions:
            dependencies[def_item.key] = []
            for rule in def_item.rules:
                if rule.ref in def_map:
                    dependencies[def_item.key].append(rule.ref)

        # Check for circular dependencies and contradictory rules
        self._check_rule_conflicts(definitions, def_map)

        # Topological sort
        sorted_items = []
        visited = set()
        temp_visited = set()

        def visit(key: str) -> None:
            """Visit a node in the dependency graph for topological sorting.

            Args:
                key: The key of the definition to visit.
            """
            if key in temp_visited:
                logger.warning("Circular dependency detected involving %s", key)
                return
            if key in visited:
                return

            temp_visited.add(key)
            for dep in dependencies.get(key, []):
                visit(dep)
            temp_visited.remove(key)
            visited.add(key)
            if key in def_map:
                sorted_items.append(def_map[key])

        for def_item in definitions:
            if def_item.key not in visited:
                visit(def_item.key)

        return sorted_items

    def _check_rule_conflicts(
        self, definitions: Sequence["DefBase"], def_map: Dict[str, "DefBase"]
    ):
        """Check for contradictory placement rules.

        Args:
            definitions: List of definitions to check.
            def_map: Mapping of key to definition.
        """
        # Group rules by reference
        rules_by_ref: Dict[str, List[Tuple[str, PlacementRule]]] = {}
        for def_item in definitions:
            for rule in def_item.rules:
                if rule.ref not in rules_by_ref:
                    rules_by_ref[rule.ref] = []
                rules_by_ref[rule.ref].append((def_item.key, rule))

        # Check for conflicts
        for ref, rules in rules_by_ref.items():
            if ref not in def_map:
                continue

            before_rules = [r for _, r in rules if r.before]
            after_rules = [r for _, r in rules if not r.before]

            if before_rules and after_rules:
                logger.warning(
                    "Contradictory placement rules for %s: %d before rules, "
                    "%d after rules",
                    ref,
                    len(before_rules),
                    len(after_rules),
                )

    def create_command_palette(
        self, ctx: "QtContext", parent: "QWidget"
    ) -> "CommandPalette":
        """Create a command palette for the application."""
        from exdrf_qt.controls.command_palette.line_edit import CommandPalette

        result = CommandPalette(
            ctx,
            parent,
            action_defs=cast(
                "List[ActionDef]",
                [
                    def_item
                    for def_item in self.defs.values()
                    if isinstance(def_item, ActionDef)
                    and not def_item.no_command_palette
                ],
            ),
        )
        return result


exdrf_qt_pm.add_hookspecs(NewMenus)
