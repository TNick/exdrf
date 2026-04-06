from typing import Any, Optional

from exdrf.filter import FieldFilter
from pydantic import BaseModel


class FilterItem(BaseModel):
    """
    An item in a filter list.

    Valid examples:

    - { "fld": "id", "op": "==", "vl": 1 }
    - { "fld": "deleted", "op": true }
    - { "fld": "age", "op": ">=", "vl": 18 }

    Attributes:
        fld: the column or other identifier that indicates
            the subject of the filter;
        op: the operation that is used to filter
            (something like ``==``, ``!=``);
        vl: the value to compare the field against;
            for some operations this might be required,
            for others may not be used at all;
    """

    fld: str
    op: str
    vl: Optional[Any] = None

    class Config:
        from_attributes = True
        populate_by_name = True

    @property
    def as_op(self):
        """
        Create the filter operation from parsed object.
        """
        return FieldFilter(fld=self.fld, op=self.op, vl=self.vl)
