# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/m_ocm.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING, Union

from sqlalchemy import select
from sqlalchemy.orm import load_only

from exdrf_dev.qt_gen.db.profiles.fields.fld_bio import BioField
from exdrf_dev.qt_gen.db.profiles.fields.fld_id import IdField
from exdrf_dev.qt_gen.db.profiles.fields.fld_parent import ParentField
from exdrf_dev.qt_gen.db.profiles.fields.fld_parent_id import ParentIdField
from exdrf_dev.qt_gen.db.profiles.fields.single_f import LabelField
from exdrf_dev.qt_gen.db.profiles.models.profile_ful import QtProfileFuMo

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401


class QtProfileNaMo(QtProfileFuMo):
    """The model that contains only the label field of the
    Profile table.

    This model is suitable for a selector or a combobox.
    """

    def __init__(
        self, selection: Union["Select", None] = None, fields=None, **kwargs
    ):
        from exdrf_dev.db.api import Profile as DbProfile

        super().__init__(
            selection=(
                selection
                if selection is not None
                else select(DbProfile).options(
                    load_only(
                        DbProfile.bio,
                        DbProfile.id,
                    )
                )
            ),
            fields=(
                fields
                if fields is not None
                else [
                    BioField,
                    ParentField,
                    ParentIdField,
                    IdField,
                    LabelField,
                ]
            ),
            **kwargs,
        )
        self.column_fields = ["label"]
