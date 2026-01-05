from collections import OrderedDict as OrDi
from typing import TYPE_CHECKING, List, Optional, OrderedDict, Tuple

if TYPE_CHECKING:
    from exdrf_qt.models.field import QtField  # noqa: F401


class FieldsList:
    """Keeps a list of fields.

    The class has no special requirement (is self-contained) and can be used
    in any class that needs to keep a list of fields.

    Attributes:
        _fields: All the fields as an ordered dictionary.
        _s_s_fields: The fields that can be used for simple search.
        _f_fields: The fields that can be used for filtering.
        _s_fields: The fields that can be used for sorting.
        _c_fields: The fields that should be presented as columns.
        _e_fields: The fields that can be exported.
    """

    _fields: OrderedDict[str, "QtField"]
    _s_s_fields: List["QtField"]
    _f_fields: List["QtField"]
    _s_fields: List["QtField"]
    _c_fields: List["QtField"]
    _e_fields: List["QtField"]

    _s_s_enabled: List[bool]

    @property
    def fields(self) -> List["QtField"]:
        """Return the list of all fields."""
        return list(self._fields.values())

    @fields.setter
    def fields(self, value: List["QtField"]):
        """Saves the list of fields and creates sub-lists for quick access.

        Args:
            value: The list of fields.
        """
        # Attempt to preserve the active/inactive state of the simple
        # search fields.
        if hasattr(self, "_s_s_enabled"):
            previous_active_state = {
                fld.name: self._s_s_enabled[i]
                for i, fld in enumerate(self._s_s_fields)
            }
        else:
            previous_active_state = {}

        self._fields = OrDi()
        self._s_s_fields = []
        self._s_s_enabled = []
        self._f_fields = []
        self._s_fields = []
        self._c_fields = []
        self._e_fields = []
        self._pk_fields = []
        for f in value:
            if isinstance(f, type) or callable(f):
                f = f(ctx=self.ctx, resource=self)  # type: ignore
            self._fields[f.name] = f

            if f.qsearch:
                self._s_s_fields.append(f)
                self._s_s_enabled.append(
                    previous_active_state.get(f.name, True)
                )

            if f.filterable:
                self._f_fields.append(f)

            if f.sortable:
                self._s_fields.append(f)

            if f.visible:
                self._c_fields.append(f)

            if f.exportable:
                self._e_fields.append(f)

            if f.primary:
                self._pk_fields.append(f)

    def get_field(
        self, key: str, raise_e: Optional[bool] = True
    ) -> Optional["QtField"]:
        """Return a field by key.

        Args:
            key: The key of the field.
            raise_e: If True, raise an error if the field is not found.

        Returns:
            The field or None if not found.
        """
        if raise_e:
            return self._fields[key]
        return self._fields.get(key)

    @property
    def simple_search_fields(self) -> List["QtField"]:
        """Return the fields that can be searched."""
        return self._s_s_fields

    @simple_search_fields.setter
    def simple_search_fields(self, value: List[str]):
        """Set the fields that can be searched.

        Args:
            value: The list of fields.
        """
        self._s_s_fields = [self._fields[f] for f in value]

    @property
    def simple_search_enabled_fields(self) -> List["QtField"]:
        """Return the fields that are active for simple search."""
        return [
            fld
            for fld, enabled in zip(self._s_s_fields, self._s_s_enabled)
            if enabled
        ]

    @property
    def simple_search_field_states(self) -> List[Tuple[bool, "QtField"]]:
        """Return the state of each field for simple search."""
        return list(zip(self._s_s_enabled, self._s_s_fields))

    def remove_from_ssf(self, field: str):
        """Remove a field from the simple search fields.

        Args:
            field: The name of the field to remove.

        Returns:
            The updated list of simple search fields.
        """
        self._s_s_fields = [f for f in self._s_s_fields if f.name != field]
        return self._s_s_fields

    @property
    def filter_fields(self) -> List["QtField"]:
        """Return the fields that can be filtered."""
        return self._f_fields

    @filter_fields.setter
    def filter_fields(self, value: List[str]):
        """Set the fields that can be filtered.

        Args:
            value: The list of fields.
        """
        self._f_fields = [self._fields[f] for f in value]

    def remove_from_ff(self, field: str):
        """Remove a field from the filter fields.

        Args:
            field: The name of the field to remove.

        Returns:
            The updated list of filter fields.
        """
        self._f_fields = [f for f in self._f_fields if f.name != field]
        return self._f_fields

    @property
    def sortable_fields(self) -> List["QtField"]:
        """Return the fields that can be sorted."""
        return self._s_fields

    @sortable_fields.setter
    def sortable_fields(self, value: List[str]):
        """Set the fields that can be sorted.

        Args:
            value: The list of fields.
        """
        self._s_fields = [self._fields[f] for f in value]

    def remove_from_sf(self, field: str):
        """Remove a field from the sortable fields.

        Args:
            field: The name of the field to remove.

        Returns:
            The updated list of sortable fields.
        """
        self._s_fields = [f for f in self._s_fields if f.name != field]
        return self._s_fields

    @property
    def column_fields(self) -> List["QtField"]:
        """Return the fields that can be displayed in a column."""
        return self._c_fields

    @column_fields.setter
    def column_fields(self, value: List[str]):
        """Set the fields that can be displayed in a column.

        Args:
            value: The list of fields.
        """
        self._c_fields = [self._fields[f] for f in value]

    def remove_from_cf(self, field: str):
        """Remove a field from the column fields.

        Args:
            field: The name of the field to remove.

        Returns:
            The updated list of column fields.
        """
        self._c_fields = [f for f in self._c_fields if f.name != field]
        return self._c_fields

    @property
    def exportable_fields(self) -> List["QtField"]:
        """Return the fields that can be exported."""
        return self._e_fields

    @exportable_fields.setter
    def exportable_fields(self, value: List[str]):
        """Set the fields that can be exported.

        Args:
            value: The list of fields.
        """
        self._e_fields = [self._fields[f] for f in value]

    def remove_from_ef(self, field: str):
        """Remove a field from the exportable fields.

        Args:
            field: The name of the field to remove.

        Returns:
            The updated list of exportable fields.
        """
        self._e_fields = [f for f in self._e_fields if f.name != field]
        return self._e_fields

    @property
    def primary_key_fields(self) -> List["QtField"]:
        """Return the fields that are primary keys."""
        return self._pk_fields

    @primary_key_fields.setter
    def primary_key_fields(self, value: List[str]):
        """Set the fields that are primary keys.

        Args:
            value: The list of fields.
        """
        self._pk_fields = [self._fields[f] for f in value]

    def remove_from_pkf(self, field: str):
        """Remove a field from the primary key fields.

        Args:
            field: The name of the field to remove.

        Returns:
            The updated list of primary key fields.
        """
        self._pk_fields = [f for f in self._pk_fields if f.name != field]
