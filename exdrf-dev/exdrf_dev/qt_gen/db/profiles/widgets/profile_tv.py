import logging
from typing import TYPE_CHECKING, Any, Callable, Union

from exdrf.constants import RecIdType
from exdrf.field_types.api import (
    IntField,
    RefOneToOneField,
    StrField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from exdrf_qt.controls.templ_viewer.view_page import WebEnginePage
from exdrf_qt.plugins import exdrf_qt_pm
from exdrf_qt.utils.plugins import safe_hook_call
from sqlalchemy import Select, select

# exdrf-keep-start other_imports -----------------------------------------------

# exdrf-keep-end other_imports -------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import Profile as Profile  # noqa: F401

logger = logging.getLogger(__name__)

# exdrf-keep-start other_globals -----------------------------------------------

# exdrf-keep-end other_globals -------------------------------------------------


class QtProfileTv(RecordTemplViewer):
    """Template viewer for a Profile database record."""

    # exdrf-keep-start other_attributes ----------------------------------------

    # exdrf-keep-end other_attributes ------------------------------------------

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import Profile as DbProfile

        super().__init__(
            db_model=kwargs.pop(
                "db_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.profiles.tv.model",
                    DbProfile,
                ),
            ),
            template_src=kwargs.pop(
                "template_src",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.profiles.tv.template",
                    "exdrf_dev.qt_gen/db/profiles/widgets/profile_tv.html",
                ),
            ),
            page_class=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.profiles.tv.page_class",
                ctx.get_ovr(
                    "tv.page_class",
                    WebEnginePage,
                ),
            ),
            other_actions=kwargs.pop(
                "other_actions",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.profiles.tv.extra-menus", None
                ),
            ),
            ctx=ctx,
            **kwargs,
        )
        if not self.windowTitle():
            self.setWindowTitle(
                self.t("profile.tv.title", "Profile viewer"),
            )

        # exdrf-keep-start extra_viewer_init -----------------------------------

        # exdrf-keep-end extra_viewer_init -------------------------------------

        # Inform plugins that the viewer has been created.
        safe_hook_call(exdrf_qt_pm.hook.profile_tv_created, widget=self)

    def read_record(self, session: "Session") -> Union[None, "Profile"]:
        from .db.profile import profile_label

        result = session.scalar(
            select(self.db_model).where(
                self.db_model.id == self.record_id,  # type: ignore
            )
        )

        if result is None:
            label = self.t(
                "profile.tv.title-not-found",
                f"Profile - record {self.record_id} not found",
            )
            return None
        else:
            try:
                label = self.t(
                    "profile.tv.title-found",
                    "Profile: view {name}",
                    name=profile_label(result),
                )
            except Exception as e:
                logger.error("Error getting label: %s", e, exc_info=True)
                label = "Profile viewer"

        self.ctx.set_window_title(self, label)
        return result

    def _populate_from_record(self, record: "Profile"):
        self.model.var_bag.add_fields(
            [
                (
                    StrField(
                        name="bio",
                        title="Bio",
                        description=("Biography text for the profile."),
                    ),
                    record.bio,
                ),
                (
                    RefOneToOneField(
                        name="parent",
                        title="Parent",
                    ),
                    record.parent,
                ),
                (
                    IntField(
                        name="parent_id",
                        title="Parent Id",
                        description=(
                            "Foreign key linking to the parent (must be unique)."
                        ),
                    ),
                    record.parent_id,
                ),
                (
                    IntField(
                        name="id",
                        title="Id",
                        description=("Primary key for the profile."),
                    ),
                    record.id,
                ),
            ]
        )

    def get_db_item_id(self, record: "Profile") -> RecIdType:
        return record.id

    def get_current_record_selector(self) -> Union[None, "Select"]:
        if self.record_id is None:
            return None
        return select(self.db_model).where(
            self.db_model.id == self.record_id,  # type: ignore
        )

    def get_deletion_function(
        self,
    ) -> Union[None, Callable[[Any, "Session"], bool]]:
        from exdrf_qt.utils.router import session_del_record

        return session_del_record

    # exdrf-keep-start extra_viewer_content ------------------------------------

    # exdrf-keep-end extra_viewer_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
