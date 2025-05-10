# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/m_ocm.py.j2
# Don't change it manually.

from exdrf_dev.qt_gen.db.composite_key_models.fields.single_f import LabelField
from exdrf_dev.qt_gen.db.composite_key_models.models.composite_key_model_ful import (
    QtCompositeKeyModelFuMo,
)


class QtCompositeKeyModelNaMo(QtCompositeKeyModelFuMo):
    """The model that contains only the label field of the
    CompositeKeyModel table.

    This model is suitable for a selector or a combobox.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields.append(
            LabelField,
        )
        self.column_fields = ["label"]
