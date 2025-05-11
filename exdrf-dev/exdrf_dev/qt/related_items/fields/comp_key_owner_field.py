# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtRefManyToOneField

if TYPE_CHECKING:
    from exdrf.resource import ExResource  # noqa: F401

    from exdrf_dev.db.models import RelatedItem  # noqa: F401


@define
class CompKeyOwnerField(QtRefManyToOneField["RelatedItem"]):
    """ """

    name: str = field(default="comp_key_owner", init=False)
    title: str = field(default="Comp Key Owner")
    visible: bool = field(default=True)
    nullable: bool = field(default=True)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)
    ref: "ExResource" = field(default=None, repr=False)
