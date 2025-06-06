from typing import List

from attrs import define, field
from exdrf_qt.utils.router import ExdrfRouter as BaseRouter
from exdrf_qt.utils.router import Route

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------


# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@define
class ExdrfRouter(BaseRouter):
    routes: List[Route] = field(
        factory=lambda: [
            # ---------------------- [ db ] ----------------------
            Route(
                "exdrf://navigation/resource/Child/{id:d}",
                handler=ExdrfRouter.view_child,
            ),
            Route(
                "exdrf://navigation/resource/Child",
                handler=ExdrfRouter.list_child,
            ),
            Route(
                "exdrf://navigation/resource/Child/{id:d}/edit",
                handler=ExdrfRouter.edit_child,
            ),
            Route(
                "exdrf://navigation/resource/Child/create",
                handler=ExdrfRouter.create_child,
            ),
            Route(
                "exdrf://navigation/resource/Child/{id:d}/delete",
                handler=ExdrfRouter.delete_child,
            ),
            Route(
                "exdrf://navigation/resource/CompositeKeyModel/{key_part1:s},{key_part2:d}",
                handler=ExdrfRouter.view_composite_key_model,
            ),
            Route(
                "exdrf://navigation/resource/CompositeKeyModel",
                handler=ExdrfRouter.list_composite_key_model,
            ),
            Route(
                "exdrf://navigation/resource/CompositeKeyModel/{key_part1:s},{key_part2:d}/edit",
                handler=ExdrfRouter.edit_composite_key_model,
            ),
            Route(
                "exdrf://navigation/resource/CompositeKeyModel/create",
                handler=ExdrfRouter.create_composite_key_model,
            ),
            Route(
                "exdrf://navigation/resource/CompositeKeyModel/{key_part1:s},{key_part2:d}/delete",
                handler=ExdrfRouter.delete_composite_key_model,
            ),
            Route(
                "exdrf://navigation/resource/Parent/{id:d}",
                handler=ExdrfRouter.view_parent,
            ),
            Route(
                "exdrf://navigation/resource/Parent",
                handler=ExdrfRouter.list_parent,
            ),
            Route(
                "exdrf://navigation/resource/Parent/{id:d}/edit",
                handler=ExdrfRouter.edit_parent,
            ),
            Route(
                "exdrf://navigation/resource/Parent/create",
                handler=ExdrfRouter.create_parent,
            ),
            Route(
                "exdrf://navigation/resource/Parent/{id:d}/delete",
                handler=ExdrfRouter.delete_parent,
            ),
            Route(
                "exdrf://navigation/resource/ParentTagAssociation/{parent_id:d},{tag_id:d}",
                handler=ExdrfRouter.view_parent_tag_association,
            ),
            Route(
                "exdrf://navigation/resource/ParentTagAssociation",
                handler=ExdrfRouter.list_parent_tag_association,
            ),
            Route(
                "exdrf://navigation/resource/ParentTagAssociation/{parent_id:d},{tag_id:d}/edit",
                handler=ExdrfRouter.edit_parent_tag_association,
            ),
            Route(
                "exdrf://navigation/resource/ParentTagAssociation/create",
                handler=ExdrfRouter.create_parent_tag_association,
            ),
            Route(
                "exdrf://navigation/resource/ParentTagAssociation/{parent_id:d},{tag_id:d}/delete",
                handler=ExdrfRouter.delete_parent_tag_association,
            ),
            Route(
                "exdrf://navigation/resource/Profile/{id:d}",
                handler=ExdrfRouter.view_profile,
            ),
            Route(
                "exdrf://navigation/resource/Profile",
                handler=ExdrfRouter.list_profile,
            ),
            Route(
                "exdrf://navigation/resource/Profile/{id:d}/edit",
                handler=ExdrfRouter.edit_profile,
            ),
            Route(
                "exdrf://navigation/resource/Profile/create",
                handler=ExdrfRouter.create_profile,
            ),
            Route(
                "exdrf://navigation/resource/Profile/{id:d}/delete",
                handler=ExdrfRouter.delete_profile,
            ),
            Route(
                "exdrf://navigation/resource/RelatedItem/{id:d}",
                handler=ExdrfRouter.view_related_item,
            ),
            Route(
                "exdrf://navigation/resource/RelatedItem",
                handler=ExdrfRouter.list_related_item,
            ),
            Route(
                "exdrf://navigation/resource/RelatedItem/{id:d}/edit",
                handler=ExdrfRouter.edit_related_item,
            ),
            Route(
                "exdrf://navigation/resource/RelatedItem/create",
                handler=ExdrfRouter.create_related_item,
            ),
            Route(
                "exdrf://navigation/resource/RelatedItem/{id:d}/delete",
                handler=ExdrfRouter.delete_related_item,
            ),
            Route(
                "exdrf://navigation/resource/Tag/{id:d}",
                handler=ExdrfRouter.view_tag,
            ),
            Route(
                "exdrf://navigation/resource/Tag",
                handler=ExdrfRouter.list_tag,
            ),
            Route(
                "exdrf://navigation/resource/Tag/{id:d}/edit",
                handler=ExdrfRouter.edit_tag,
            ),
            Route(
                "exdrf://navigation/resource/Tag/create",
                handler=ExdrfRouter.create_tag,
            ),
            Route(
                "exdrf://navigation/resource/Tag/{id:d}/delete",
                handler=ExdrfRouter.delete_tag,
            ),
        ]
    )

    # exdrf-keep-start other_router_attributes ---------------------------------

    # exdrf-keep-end other_router_attributes -----------------------------------

    # -------------------------- [ db ] --------------------------

    @staticmethod
    def view_child(router: "ExdrfRouter", id: int):
        from exdrf_dev.qt_gen.db.children.api import (
            QtChildTv,
        )

        router.open_viewer(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.children.qt.viewer", QtChildTv
            ),
            id=(id),
        )

    @staticmethod
    def list_child(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.children.api import QtChildList

        router.open_list(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.children.qt.list", QtChildList
            )
        )

    @staticmethod
    def edit_child(router: "ExdrfRouter", id: int):
        from exdrf_dev.qt_gen.db.children.api import (
            QtChildEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.children.qt.editor", QtChildEditor
            ),
            id=(id),
        )

    @staticmethod
    def create_child(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.children.api import (
            QtChildEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.children.qt.editor", QtChildEditor
            ),
        )

    @staticmethod
    def delete_child(router: "ExdrfRouter", id: int):
        from exdrf_dev.db.api import Child

        router.delete_record(Child, id=(id))

    @staticmethod
    def view_composite_key_model(
        router: "ExdrfRouter", key_part1: str, key_part2: int
    ):
        from exdrf_dev.qt_gen.db.composite_key_models.api import (
            QtCompositeKeyModelTv,
        )

        router.open_viewer(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.qt.viewer",
                QtCompositeKeyModelTv,
            ),
            id=(key_part1, key_part2),
        )

    @staticmethod
    def list_composite_key_model(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.composite_key_models.api import (
            QtCompositeKeyModelList,
        )

        router.open_list(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.qt.list",
                QtCompositeKeyModelList,
            )
        )

    @staticmethod
    def edit_composite_key_model(
        router: "ExdrfRouter", key_part1: str, key_part2: int
    ):
        from exdrf_dev.qt_gen.db.composite_key_models.api import (
            QtCompositeKeyModelEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.qt.editor",
                QtCompositeKeyModelEditor,
            ),
            id=(key_part1, key_part2),
        )

    @staticmethod
    def create_composite_key_model(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.composite_key_models.api import (
            QtCompositeKeyModelEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.qt.editor",
                QtCompositeKeyModelEditor,
            ),
        )

    @staticmethod
    def delete_composite_key_model(
        router: "ExdrfRouter", key_part1: str, key_part2: int
    ):
        from exdrf_dev.db.api import CompositeKeyModel

        router.delete_record(CompositeKeyModel, id=(key_part1, key_part2))

    @staticmethod
    def view_parent(router: "ExdrfRouter", id: int):
        from exdrf_dev.qt_gen.db.parents.api import (
            QtParentTv,
        )

        router.open_viewer(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parents.qt.viewer", QtParentTv
            ),
            id=(id),
        )

    @staticmethod
    def list_parent(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.parents.api import QtParentList

        router.open_list(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parents.qt.list", QtParentList
            )
        )

    @staticmethod
    def edit_parent(router: "ExdrfRouter", id: int):
        from exdrf_dev.qt_gen.db.parents.api import (
            QtParentEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parents.qt.editor", QtParentEditor
            ),
            id=(id),
        )

    @staticmethod
    def create_parent(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.parents.api import (
            QtParentEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parents.qt.editor", QtParentEditor
            ),
        )

    @staticmethod
    def delete_parent(router: "ExdrfRouter", id: int):
        from exdrf_dev.db.api import Parent

        router.delete_record(Parent, id=(id))

    @staticmethod
    def view_parent_tag_association(
        router: "ExdrfRouter", parent_id: int, tag_id: int
    ):
        from exdrf_dev.qt_gen.db.parent_tag_associations.api import (
            QtParentTagAssociationTv,
        )

        router.open_viewer(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parent_tag_associations.qt.viewer",
                QtParentTagAssociationTv,
            ),
            id=(parent_id, tag_id),
        )

    @staticmethod
    def list_parent_tag_association(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.parent_tag_associations.api import (
            QtParentTagAssociationList,
        )

        router.open_list(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parent_tag_associations.qt.list",
                QtParentTagAssociationList,
            )
        )

    @staticmethod
    def edit_parent_tag_association(
        router: "ExdrfRouter", parent_id: int, tag_id: int
    ):
        from exdrf_dev.qt_gen.db.parent_tag_associations.api import (
            QtParentTagAssociationEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parent_tag_associations.qt.editor",
                QtParentTagAssociationEditor,
            ),
            id=(parent_id, tag_id),
        )

    @staticmethod
    def create_parent_tag_association(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.parent_tag_associations.api import (
            QtParentTagAssociationEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parent_tag_associations.qt.editor",
                QtParentTagAssociationEditor,
            ),
        )

    @staticmethod
    def delete_parent_tag_association(
        router: "ExdrfRouter", parent_id: int, tag_id: int
    ):
        from exdrf_dev.db.api import ParentTagAssociation

        router.delete_record(ParentTagAssociation, id=(parent_id, tag_id))

    @staticmethod
    def view_profile(router: "ExdrfRouter", id: int):
        from exdrf_dev.qt_gen.db.profiles.api import (
            QtProfileTv,
        )

        router.open_viewer(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.profiles.qt.viewer", QtProfileTv
            ),
            id=(id),
        )

    @staticmethod
    def list_profile(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.profiles.api import QtProfileList

        router.open_list(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.profiles.qt.list", QtProfileList
            )
        )

    @staticmethod
    def edit_profile(router: "ExdrfRouter", id: int):
        from exdrf_dev.qt_gen.db.profiles.api import (
            QtProfileEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.profiles.qt.editor", QtProfileEditor
            ),
            id=(id),
        )

    @staticmethod
    def create_profile(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.profiles.api import (
            QtProfileEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.profiles.qt.editor", QtProfileEditor
            ),
        )

    @staticmethod
    def delete_profile(router: "ExdrfRouter", id: int):
        from exdrf_dev.db.api import Profile

        router.delete_record(Profile, id=(id))

    @staticmethod
    def view_related_item(router: "ExdrfRouter", id: int):
        from exdrf_dev.qt_gen.db.related_items.api import (
            QtRelatedItemTv,
        )

        router.open_viewer(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.related_items.qt.viewer", QtRelatedItemTv
            ),
            id=(id),
        )

    @staticmethod
    def list_related_item(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.related_items.api import QtRelatedItemList

        router.open_list(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.related_items.qt.list", QtRelatedItemList
            )
        )

    @staticmethod
    def edit_related_item(router: "ExdrfRouter", id: int):
        from exdrf_dev.qt_gen.db.related_items.api import (
            QtRelatedItemEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.related_items.qt.editor",
                QtRelatedItemEditor,
            ),
            id=(id),
        )

    @staticmethod
    def create_related_item(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.related_items.api import (
            QtRelatedItemEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.related_items.qt.editor",
                QtRelatedItemEditor,
            ),
        )

    @staticmethod
    def delete_related_item(router: "ExdrfRouter", id: int):
        from exdrf_dev.db.api import RelatedItem

        router.delete_record(RelatedItem, id=(id))

    @staticmethod
    def view_tag(router: "ExdrfRouter", id: int):
        from exdrf_dev.qt_gen.db.tags.api import (
            QtTagTv,
        )

        router.open_viewer(
            router.ctx.get_ovr("exdrf_dev.qt_gen.db.tags.qt.viewer", QtTagTv),
            id=(id),
        )

    @staticmethod
    def list_tag(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.tags.api import QtTagList

        router.open_list(
            router.ctx.get_ovr("exdrf_dev.qt_gen.db.tags.qt.list", QtTagList)
        )

    @staticmethod
    def edit_tag(router: "ExdrfRouter", id: int):
        from exdrf_dev.qt_gen.db.tags.api import (
            QtTagEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.tags.qt.editor", QtTagEditor
            ),
            id=(id),
        )

    @staticmethod
    def create_tag(router: "ExdrfRouter"):
        from exdrf_dev.qt_gen.db.tags.api import (
            QtTagEditor,
        )

        router.open_editor(
            router.ctx.get_ovr(
                "exdrf_dev.qt_gen.db.tags.qt.editor", QtTagEditor
            ),
        )

    @staticmethod
    def delete_tag(router: "ExdrfRouter", id: int):
        from exdrf_dev.db.api import Tag

        router.delete_record(Tag, id=(id))

    # exdrf-keep-start extra_router_content ------------------------------------

    # exdrf-keep-end extra_router_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
