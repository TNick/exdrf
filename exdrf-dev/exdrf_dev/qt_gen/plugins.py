# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> plugins.py.j2
# Don't change it manually.
import logging
from typing import TYPE_CHECKING, Optional

from exdrf_qt.plugins import hook_spec

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf.filter import FilterType  # noqa: F401

    from exdrf_dev.qt_gen.db.children.api import QtChildEditor  # noqa: F401
    from exdrf_dev.qt_gen.db.children.api import QtChildFuMo  # noqa: F401
    from exdrf_dev.qt_gen.db.children.api import QtChildList  # noqa: F401
    from exdrf_dev.qt_gen.db.children.api import QtChildMuSe  # noqa: F401
    from exdrf_dev.qt_gen.db.children.api import QtChildNaMo  # noqa: F401
    from exdrf_dev.qt_gen.db.children.api import QtChildSiSe  # noqa: F401
    from exdrf_dev.qt_gen.db.children.api import QtChildTv  # noqa: F401
    from exdrf_dev.qt_gen.db.composite_key_models.api import (  # noqa: F401
        QtCompositeKeyModelEditor,
    )
    from exdrf_dev.qt_gen.db.composite_key_models.api import (  # noqa: F401
        QtCompositeKeyModelFuMo,
    )
    from exdrf_dev.qt_gen.db.composite_key_models.api import (  # noqa: F401
        QtCompositeKeyModelList,
    )
    from exdrf_dev.qt_gen.db.composite_key_models.api import (  # noqa: F401
        QtCompositeKeyModelMuSe,
    )
    from exdrf_dev.qt_gen.db.composite_key_models.api import (  # noqa: F401
        QtCompositeKeyModelNaMo,
    )
    from exdrf_dev.qt_gen.db.composite_key_models.api import (  # noqa: F401
        QtCompositeKeyModelSiSe,
    )
    from exdrf_dev.qt_gen.db.composite_key_models.api import (  # noqa: F401
        QtCompositeKeyModelTv,
    )
    from exdrf_dev.qt_gen.db.parent_tag_associations.api import (  # noqa: F401
        QtParentTagAssociationEditor,
    )
    from exdrf_dev.qt_gen.db.parent_tag_associations.api import (  # noqa: F401
        QtParentTagAssociationFuMo,
    )
    from exdrf_dev.qt_gen.db.parent_tag_associations.api import (  # noqa: F401
        QtParentTagAssociationList,
    )
    from exdrf_dev.qt_gen.db.parent_tag_associations.api import (  # noqa: F401
        QtParentTagAssociationMuSe,
    )
    from exdrf_dev.qt_gen.db.parent_tag_associations.api import (  # noqa: F401
        QtParentTagAssociationNaMo,
    )
    from exdrf_dev.qt_gen.db.parent_tag_associations.api import (  # noqa: F401
        QtParentTagAssociationSiSe,
    )
    from exdrf_dev.qt_gen.db.parent_tag_associations.api import (  # noqa: F401
        QtParentTagAssociationTv,
    )
    from exdrf_dev.qt_gen.db.parents.api import QtParentEditor  # noqa: F401
    from exdrf_dev.qt_gen.db.parents.api import QtParentFuMo  # noqa: F401
    from exdrf_dev.qt_gen.db.parents.api import QtParentList  # noqa: F401
    from exdrf_dev.qt_gen.db.parents.api import QtParentMuSe  # noqa: F401
    from exdrf_dev.qt_gen.db.parents.api import QtParentNaMo  # noqa: F401
    from exdrf_dev.qt_gen.db.parents.api import QtParentSiSe  # noqa: F401
    from exdrf_dev.qt_gen.db.parents.api import QtParentTv  # noqa: F401
    from exdrf_dev.qt_gen.db.profiles.api import QtProfileEditor  # noqa: F401
    from exdrf_dev.qt_gen.db.profiles.api import QtProfileFuMo  # noqa: F401
    from exdrf_dev.qt_gen.db.profiles.api import QtProfileList  # noqa: F401
    from exdrf_dev.qt_gen.db.profiles.api import QtProfileMuSe  # noqa: F401
    from exdrf_dev.qt_gen.db.profiles.api import QtProfileNaMo  # noqa: F401
    from exdrf_dev.qt_gen.db.profiles.api import QtProfileSiSe  # noqa: F401
    from exdrf_dev.qt_gen.db.profiles.api import QtProfileTv  # noqa: F401
    from exdrf_dev.qt_gen.db.related_items.api import (
        QtRelatedItemEditor,
    )  # noqa: F401
    from exdrf_dev.qt_gen.db.related_items.api import (
        QtRelatedItemFuMo,
    )  # noqa: F401
    from exdrf_dev.qt_gen.db.related_items.api import (
        QtRelatedItemList,
    )  # noqa: F401
    from exdrf_dev.qt_gen.db.related_items.api import (
        QtRelatedItemMuSe,
    )  # noqa: F401
    from exdrf_dev.qt_gen.db.related_items.api import (
        QtRelatedItemNaMo,
    )  # noqa: F401
    from exdrf_dev.qt_gen.db.related_items.api import (
        QtRelatedItemSiSe,
    )  # noqa: F401
    from exdrf_dev.qt_gen.db.related_items.api import (
        QtRelatedItemTv,
    )  # noqa: F401
    from exdrf_dev.qt_gen.db.tags.api import QtTagEditor  # noqa: F401
    from exdrf_dev.qt_gen.db.tags.api import QtTagFuMo  # noqa: F401
    from exdrf_dev.qt_gen.db.tags.api import QtTagList  # noqa: F401
    from exdrf_dev.qt_gen.db.tags.api import QtTagMuSe  # noqa: F401
    from exdrf_dev.qt_gen.db.tags.api import QtTagNaMo  # noqa: F401
    from exdrf_dev.qt_gen.db.tags.api import QtTagSiSe  # noqa: F401
    from exdrf_dev.qt_gen.db.tags.api import QtTagTv  # noqa: F401

logger = logging.getLogger(__name__)
# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


class ChildHooks:
    """Hooks related to the Child resource."""

    @hook_spec
    def child_fumo_created(self, model: "QtChildFuMo") -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def child_fumo_ttf(
        self,
        model: "QtChildFuMo",
        text: str,
        exact: Optional[bool],
        limit: Optional[str],
        filters: "FilterType",
    ) -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def child_namo_created(self, model: "QtChildNaMo") -> None:
        """Called when a name model is created."""
        raise NotImplementedError

    @hook_spec
    def child_editor_created(self, widget: "QtChildEditor") -> None:
        """Called when an editor of an item is created."""
        raise NotImplementedError

    @hook_spec
    def child_list_created(self, widget: "QtChildList") -> None:
        """Called when a list of items is created."""
        raise NotImplementedError

    @hook_spec
    def child_sise_created(self, widget: "QtChildSiSe") -> None:
        """Called when a single-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def child_muse_created(self, widget: "QtChildMuSe") -> None:
        """Called when a multi-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def child_tv_created(self, widget: "QtChildTv") -> None:
        """Called when a template-based viewer is created."""
        raise NotImplementedError


class CompositeKeyModelHooks:
    """Hooks related to the CompositeKeyModel resource."""

    @hook_spec
    def composite_key_model_fumo_created(
        self, model: "QtCompositeKeyModelFuMo"
    ) -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def composite_key_model_fumo_ttf(
        self,
        model: "QtCompositeKeyModelFuMo",
        text: str,
        exact: Optional[bool],
        limit: Optional[str],
        filters: "FilterType",
    ) -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def composite_key_model_namo_created(
        self, model: "QtCompositeKeyModelNaMo"
    ) -> None:
        """Called when a name model is created."""
        raise NotImplementedError

    @hook_spec
    def composite_key_model_editor_created(
        self, widget: "QtCompositeKeyModelEditor"
    ) -> None:
        """Called when an editor of an item is created."""
        raise NotImplementedError

    @hook_spec
    def composite_key_model_list_created(
        self, widget: "QtCompositeKeyModelList"
    ) -> None:
        """Called when a list of items is created."""
        raise NotImplementedError

    @hook_spec
    def composite_key_model_sise_created(
        self, widget: "QtCompositeKeyModelSiSe"
    ) -> None:
        """Called when a single-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def composite_key_model_muse_created(
        self, widget: "QtCompositeKeyModelMuSe"
    ) -> None:
        """Called when a multi-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def composite_key_model_tv_created(
        self, widget: "QtCompositeKeyModelTv"
    ) -> None:
        """Called when a template-based viewer is created."""
        raise NotImplementedError


class ParentHooks:
    """Hooks related to the Parent resource."""

    @hook_spec
    def parent_fumo_created(self, model: "QtParentFuMo") -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def parent_fumo_ttf(
        self,
        model: "QtParentFuMo",
        text: str,
        exact: Optional[bool],
        limit: Optional[str],
        filters: "FilterType",
    ) -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def parent_namo_created(self, model: "QtParentNaMo") -> None:
        """Called when a name model is created."""
        raise NotImplementedError

    @hook_spec
    def parent_editor_created(self, widget: "QtParentEditor") -> None:
        """Called when an editor of an item is created."""
        raise NotImplementedError

    @hook_spec
    def parent_list_created(self, widget: "QtParentList") -> None:
        """Called when a list of items is created."""
        raise NotImplementedError

    @hook_spec
    def parent_sise_created(self, widget: "QtParentSiSe") -> None:
        """Called when a single-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def parent_muse_created(self, widget: "QtParentMuSe") -> None:
        """Called when a multi-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def parent_tv_created(self, widget: "QtParentTv") -> None:
        """Called when a template-based viewer is created."""
        raise NotImplementedError


class ParentTagAssociationHooks:
    """Hooks related to the ParentTagAssociation resource."""

    @hook_spec
    def parent_tag_association_fumo_created(
        self, model: "QtParentTagAssociationFuMo"
    ) -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def parent_tag_association_fumo_ttf(
        self,
        model: "QtParentTagAssociationFuMo",
        text: str,
        exact: Optional[bool],
        limit: Optional[str],
        filters: "FilterType",
    ) -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def parent_tag_association_namo_created(
        self, model: "QtParentTagAssociationNaMo"
    ) -> None:
        """Called when a name model is created."""
        raise NotImplementedError

    @hook_spec
    def parent_tag_association_editor_created(
        self, widget: "QtParentTagAssociationEditor"
    ) -> None:
        """Called when an editor of an item is created."""
        raise NotImplementedError

    @hook_spec
    def parent_tag_association_list_created(
        self, widget: "QtParentTagAssociationList"
    ) -> None:
        """Called when a list of items is created."""
        raise NotImplementedError

    @hook_spec
    def parent_tag_association_sise_created(
        self, widget: "QtParentTagAssociationSiSe"
    ) -> None:
        """Called when a single-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def parent_tag_association_muse_created(
        self, widget: "QtParentTagAssociationMuSe"
    ) -> None:
        """Called when a multi-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def parent_tag_association_tv_created(
        self, widget: "QtParentTagAssociationTv"
    ) -> None:
        """Called when a template-based viewer is created."""
        raise NotImplementedError


class ProfileHooks:
    """Hooks related to the Profile resource."""

    @hook_spec
    def profile_fumo_created(self, model: "QtProfileFuMo") -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def profile_fumo_ttf(
        self,
        model: "QtProfileFuMo",
        text: str,
        exact: Optional[bool],
        limit: Optional[str],
        filters: "FilterType",
    ) -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def profile_namo_created(self, model: "QtProfileNaMo") -> None:
        """Called when a name model is created."""
        raise NotImplementedError

    @hook_spec
    def profile_editor_created(self, widget: "QtProfileEditor") -> None:
        """Called when an editor of an item is created."""
        raise NotImplementedError

    @hook_spec
    def profile_list_created(self, widget: "QtProfileList") -> None:
        """Called when a list of items is created."""
        raise NotImplementedError

    @hook_spec
    def profile_sise_created(self, widget: "QtProfileSiSe") -> None:
        """Called when a single-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def profile_muse_created(self, widget: "QtProfileMuSe") -> None:
        """Called when a multi-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def profile_tv_created(self, widget: "QtProfileTv") -> None:
        """Called when a template-based viewer is created."""
        raise NotImplementedError


class RelatedItemHooks:
    """Hooks related to the RelatedItem resource."""

    @hook_spec
    def related_item_fumo_created(self, model: "QtRelatedItemFuMo") -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def related_item_fumo_ttf(
        self,
        model: "QtRelatedItemFuMo",
        text: str,
        exact: Optional[bool],
        limit: Optional[str],
        filters: "FilterType",
    ) -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def related_item_namo_created(self, model: "QtRelatedItemNaMo") -> None:
        """Called when a name model is created."""
        raise NotImplementedError

    @hook_spec
    def related_item_editor_created(
        self, widget: "QtRelatedItemEditor"
    ) -> None:
        """Called when an editor of an item is created."""
        raise NotImplementedError

    @hook_spec
    def related_item_list_created(self, widget: "QtRelatedItemList") -> None:
        """Called when a list of items is created."""
        raise NotImplementedError

    @hook_spec
    def related_item_sise_created(self, widget: "QtRelatedItemSiSe") -> None:
        """Called when a single-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def related_item_muse_created(self, widget: "QtRelatedItemMuSe") -> None:
        """Called when a multi-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def related_item_tv_created(self, widget: "QtRelatedItemTv") -> None:
        """Called when a template-based viewer is created."""
        raise NotImplementedError


class TagHooks:
    """Hooks related to the Tag resource."""

    @hook_spec
    def tag_fumo_created(self, model: "QtTagFuMo") -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def tag_fumo_ttf(
        self,
        model: "QtTagFuMo",
        text: str,
        exact: Optional[bool],
        limit: Optional[str],
        filters: "FilterType",
    ) -> None:
        """Called when a full model is created."""
        raise NotImplementedError

    @hook_spec
    def tag_namo_created(self, model: "QtTagNaMo") -> None:
        """Called when a name model is created."""
        raise NotImplementedError

    @hook_spec
    def tag_editor_created(self, widget: "QtTagEditor") -> None:
        """Called when an editor of an item is created."""
        raise NotImplementedError

    @hook_spec
    def tag_list_created(self, widget: "QtTagList") -> None:
        """Called when a list of items is created."""
        raise NotImplementedError

    @hook_spec
    def tag_sise_created(self, widget: "QtTagSiSe") -> None:
        """Called when a single-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def tag_muse_created(self, widget: "QtTagMuSe") -> None:
        """Called when a multi-select widget is created."""
        raise NotImplementedError

    @hook_spec
    def tag_tv_created(self, widget: "QtTagTv") -> None:
        """Called when a template-based viewer is created."""
        raise NotImplementedError


def register_all_hooks():
    """Registers all hooks across all resources."""
    from exdrf_qt.plugins import exdrf_qt_pm

    # ------------------------------------------------------------
    # db
    # ------------------------------------------------------------
    exdrf_qt_pm.add_hookspecs(ChildHooks)
    exdrf_qt_pm.add_hookspecs(CompositeKeyModelHooks)
    exdrf_qt_pm.add_hookspecs(ParentHooks)
    exdrf_qt_pm.add_hookspecs(ParentTagAssociationHooks)
    exdrf_qt_pm.add_hookspecs(ProfileHooks)
    exdrf_qt_pm.add_hookspecs(RelatedItemHooks)
    exdrf_qt_pm.add_hookspecs(TagHooks)
