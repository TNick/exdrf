# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/m_ocm.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING, Union

from sqlalchemy import select
from sqlalchemy.orm import load_only

from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_description import (
    DescriptionField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_key_part1 import (
    KeyPart1Field,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_key_part2 import (
    KeyPart2Field,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_related_items import (
    RelatedItemsField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_some_binary import (
    SomeBinaryField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_some_date import (
    SomeDateField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_some_enum import (
    SomeEnumField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_some_float import (
    SomeFloatField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_some_json import (
    SomeJsonField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_some_time import (
    SomeTimeField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.single_f import LabelField
from exdrf_dev.qt_gen.db.composite_key_models.models.composite_key_model_ful import (
    QtCompositeKeyModelFuMo,
)

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401


class QtCompositeKeyModelNaMo(QtCompositeKeyModelFuMo):
    """The model that contains only the label field of the
    CompositeKeyModel table.

    This model is suitable for a selector or a combobox.
    """

    def __init__(
        self, selection: Union["Select", None] = None, fields=None, **kwargs
    ):
        from exdrf_dev.db.api import CompositeKeyModel as DbCompositeKeyModel

        super().__init__(
            selection=(
                selection
                if selection is not None
                else select(DbCompositeKeyModel).options(
                    load_only(
                        DbCompositeKeyModel.description,
                        DbCompositeKeyModel.key_part1,
                        DbCompositeKeyModel.key_part2,
                    )
                )
            ),
            fields=(
                fields
                if fields is not None
                else [
                    DescriptionField,
                    RelatedItemsField,
                    SomeBinaryField,
                    SomeDateField,
                    SomeEnumField,
                    SomeFloatField,
                    SomeJsonField,
                    SomeTimeField,
                    KeyPart1Field,
                    KeyPart2Field,
                    LabelField,
                ]
            ),
            **kwargs,
        )
        self.column_fields = ["label"]
