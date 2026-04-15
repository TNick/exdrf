"""Pydantic wire models for remote-controlled-view plans and field metadata.

``kind`` values mirror ``FIELD_TYPE_*`` in ``exdrf.constants``; ``data`` carries
type-specific options aligned with ``exdrf.field_types`` ``*Field`` /
``*Info`` shapes.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated, Any, Literal, Union

from exdrf.constants import (
    FIELD_TYPE_BLOB,
    FIELD_TYPE_BOOL,
    FIELD_TYPE_DATE,
    FIELD_TYPE_DT,
    FIELD_TYPE_DURATION,
    FIELD_TYPE_ENUM,
    FIELD_TYPE_FILTER,
    FIELD_TYPE_FLOAT,
    FIELD_TYPE_FLOAT_LIST,
    FIELD_TYPE_FORMATTED,
    FIELD_TYPE_INT_LIST,
    FIELD_TYPE_INTEGER,
    FIELD_TYPE_REF_MANY_TO_MANY,
    FIELD_TYPE_REF_MANY_TO_ONE,
    FIELD_TYPE_REF_ONE_TO_MANY,
    FIELD_TYPE_REF_ONE_TO_ONE,
    FIELD_TYPE_SORT,
    FIELD_TYPE_STRING,
    FIELD_TYPE_STRING_LIST,
    FIELD_TYPE_TIME,
    RelType,
)
from pydantic import BaseModel, ConfigDict, Field


class RcvFieldBase(BaseModel):
    """Shared metadata for one field in an ``RcvPlan``.

    Attributes:
        name: Field name on the resource (snake_case).
        title: Human-facing title when not inferred from ``name``.
        description: Longer help text for the field.
        category: Short logical grouping for layout.
        pos_hint: UI ordering / placement hint from ``FieldInfo``.
        required: Whether a value must be present for save/submit.
        default: Wire default when omitted (type depends on ``kind``).
        primary: Whether the field participates in record identity.
        visible: Whether the field is shown to the user.
        read_only: Whether the value is displayed but not editable.
        nullable: Whether the underlying column allows null.
        sortable: Whether list views may sort by this field.
        filterable: Whether list views may filter by this field.
        exportable: Whether user export may include this field.
        qsearch: Whether quick-search uses this field.
        resizable: Whether list column width is user-resizable.
        derived: Optional ``(derivation_kind, source_field_name)`` tuple.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    title: str | None = None
    description: str | None = None
    category: str | None = None
    pos_hint: str | None = None
    required: bool = False
    default: Any | None = None
    primary: bool | None = None
    visible: bool | None = None
    read_only: bool | None = None
    nullable: bool | None = None
    sortable: bool | None = None
    filterable: bool | None = None
    exportable: bool | None = None
    qsearch: bool | None = None
    resizable: bool | None = None
    derived: tuple[str, str] | None = None


class RcvEmptyData(BaseModel):
    """Placeholder ``data`` for field kinds without extra options."""

    model_config = ConfigDict(extra="forbid")


class RcvBlobFieldData(BaseModel):
    """Options for ``FIELD_TYPE_BLOB`` (see ``BlobInfo``)."""

    model_config = ConfigDict(extra="forbid")

    mime_type: str | None = None


class RcvBoolFieldData(BaseModel):
    """Options for ``FIELD_TYPE_BOOL`` (see ``BoolInfo``)."""

    model_config = ConfigDict(extra="forbid")

    true_str: str | None = None
    false_str: str | None = None


class RcvStringFieldData(BaseModel):
    """Options for string-like kinds (see ``StrInfo`` / ``StrListInfo``)."""

    model_config = ConfigDict(extra="forbid")

    multiline: bool | None = None
    min_length: int | None = None
    max_length: int | None = None
    enum_values: list[tuple[str, str]] = Field(default_factory=list)
    no_dia_field: str | None = None


class RcvFormattedFieldData(RcvStringFieldData):
    """Options for ``FIELD_TYPE_FORMATTED`` (see ``FormattedInfo``)."""

    format: Literal["json", "html", "xml"] | None = None


class RcvIntFieldData(BaseModel):
    """Options for ``FIELD_TYPE_INTEGER`` / ``FIELD_TYPE_INT_LIST``."""

    model_config = ConfigDict(extra="forbid")

    min: int | None = None
    max: int | None = None
    unit: str | None = None
    unit_symbol: str | None = None
    enum_values: list[tuple[int, str]] = Field(default_factory=list)


class RcvFloatFieldData(BaseModel):
    """Options for ``FIELD_TYPE_FLOAT`` / ``FIELD_TYPE_FLOAT_LIST``."""

    model_config = ConfigDict(extra="forbid")

    min: float | None = None
    max: float | None = None
    precision: int | None = None
    scale: int | None = None
    unit: str | None = None
    unit_symbol: str | None = None
    enum_values: list[tuple[float, str]] = Field(default_factory=list)


class RcvDateFieldData(BaseModel):
    """Options for ``FIELD_TYPE_DATE`` (see ``DateInfo`` + ``DateField``)."""

    model_config = ConfigDict(extra="forbid")

    min: date | None = None
    max: date | None = None
    format: str | None = None


class RcvDateTimeFieldData(BaseModel):
    """Options for ``FIELD_TYPE_DT`` (``DateTimeInfo`` / ``DateTimeField``)."""

    model_config = ConfigDict(extra="forbid")

    min: datetime | None = None
    max: datetime | None = None
    format: str | None = None


class RcvTimeFieldData(BaseModel):
    """Options for ``FIELD_TYPE_TIME`` (see ``TimeInfo`` + ``TimeField``)."""

    model_config = ConfigDict(extra="forbid")

    min: time | None = None
    max: time | None = None
    format: str | None = None


class RcvDurationFieldData(BaseModel):
    """Options for ``FIELD_TYPE_DURATION`` (see ``DurationInfo``)."""

    model_config = ConfigDict(extra="forbid")

    min: float | None = None
    max: float | None = None


class RcvEnumFieldData(BaseModel):
    """Options for ``FIELD_TYPE_ENUM`` (see ``EnumInfo`` / ``EnumField``)."""

    model_config = ConfigDict(extra="forbid")

    enum_values: list[str] = Field(default_factory=list)


class RcvRefFieldData(BaseModel):
    """Options for relation kinds (see ``RelExtraInfo`` / ``RefBaseField``)."""

    model_config = ConfigDict(extra="forbid")

    ref: str
    direction: RelType | None = None
    subordinate: bool | None = None
    expect_lots: bool | None = None
    provides: list[str] = Field(default_factory=list)
    depends_on: list[tuple[str, str]] = Field(default_factory=list)
    bridge: str | None = None


class RcvBlobField(RcvFieldBase):
    """RCV descriptor for a blob column."""

    kind: Literal["blob"] = FIELD_TYPE_BLOB
    data: RcvBlobFieldData = Field(default_factory=RcvBlobFieldData)


class RcvBoolField(RcvFieldBase):
    """RCV descriptor for a boolean column."""

    kind: Literal["bool"] = FIELD_TYPE_BOOL
    data: RcvBoolFieldData = Field(default_factory=RcvBoolFieldData)


class RcvDateField(RcvFieldBase):
    """RCV descriptor for a date column."""

    kind: Literal["date"] = FIELD_TYPE_DATE
    data: RcvDateFieldData = Field(default_factory=RcvDateFieldData)


class RcvDateTimeField(RcvFieldBase):
    """RCV descriptor for a date-time column."""

    kind: Literal["date-time"] = FIELD_TYPE_DT
    data: RcvDateTimeFieldData = Field(default_factory=RcvDateTimeFieldData)


class RcvDurationField(RcvFieldBase):
    """RCV descriptor for a duration column."""

    kind: Literal["duration"] = FIELD_TYPE_DURATION
    data: RcvDurationFieldData = Field(default_factory=RcvDurationFieldData)


class RcvEnumField(RcvFieldBase):
    """RCV descriptor for an enum-like column."""

    kind: Literal["enum"] = FIELD_TYPE_ENUM
    data: RcvEnumFieldData = Field(default_factory=RcvEnumFieldData)


class RcvFilterField(RcvFieldBase):
    """RCV descriptor for a filter pseudo-field."""

    kind: Literal["filter"] = FIELD_TYPE_FILTER
    data: RcvEmptyData = Field(default_factory=RcvEmptyData)


class RcvFloatField(RcvFieldBase):
    """RCV descriptor for a float column."""

    kind: Literal["float"] = FIELD_TYPE_FLOAT
    data: RcvFloatFieldData = Field(default_factory=RcvFloatFieldData)


class RcvFloatListField(RcvFieldBase):
    """RCV descriptor for a float list column."""

    kind: Literal["float-list"] = FIELD_TYPE_FLOAT_LIST
    data: RcvFloatFieldData = Field(default_factory=RcvFloatFieldData)


class RcvFormattedField(RcvFieldBase):
    """RCV descriptor for formatted (rich text / markup) string columns."""

    kind: Literal["formatted"] = FIELD_TYPE_FORMATTED
    data: RcvFormattedFieldData = Field(default_factory=RcvFormattedFieldData)


class RcvIntField(RcvFieldBase):
    """RCV descriptor for an integer column."""

    kind: Literal["integer"] = FIELD_TYPE_INTEGER
    data: RcvIntFieldData = Field(default_factory=RcvIntFieldData)


class RcvIntListField(RcvFieldBase):
    """RCV descriptor for an integer list column."""

    kind: Literal["int-list"] = FIELD_TYPE_INT_LIST
    data: RcvIntFieldData = Field(default_factory=RcvIntFieldData)


class RcvManyToManyField(RcvFieldBase):
    """RCV descriptor for a many-to-many relation field."""

    kind: Literal["many-to-many"] = FIELD_TYPE_REF_MANY_TO_MANY
    data: RcvRefFieldData


class RcvManyToOneField(RcvFieldBase):
    """RCV descriptor for a many-to-one relation field."""

    kind: Literal["many-to-one"] = FIELD_TYPE_REF_MANY_TO_ONE
    data: RcvRefFieldData


class RcvOneToManyField(RcvFieldBase):
    """RCV descriptor for a one-to-many relation field."""

    kind: Literal["one-to-many"] = FIELD_TYPE_REF_ONE_TO_MANY
    data: RcvRefFieldData


class RcvOneToOneField(RcvFieldBase):
    """RCV descriptor for a one-to-one relation field."""

    kind: Literal["one-to-one"] = FIELD_TYPE_REF_ONE_TO_ONE
    data: RcvRefFieldData


class RcvStringField(RcvFieldBase):
    """RCV descriptor for a string column."""

    kind: Literal["string"] = FIELD_TYPE_STRING
    data: RcvStringFieldData = Field(default_factory=RcvStringFieldData)


class RcvStringListField(RcvFieldBase):
    """RCV descriptor for a string list column."""

    kind: Literal["string-list"] = FIELD_TYPE_STRING_LIST
    data: RcvStringFieldData = Field(default_factory=RcvStringFieldData)


class RcvSortField(RcvFieldBase):
    """RCV descriptor for a sort pseudo-field."""

    kind: Literal["sort"] = FIELD_TYPE_SORT
    data: RcvEmptyData = Field(default_factory=RcvEmptyData)


class RcvTimeField(RcvFieldBase):
    """RCV descriptor for a time-of-day column."""

    kind: Literal["time"] = FIELD_TYPE_TIME
    data: RcvTimeFieldData = Field(default_factory=RcvTimeFieldData)


RcvField = Annotated[
    Union[
        RcvBlobField,
        RcvBoolField,
        RcvDateField,
        RcvDateTimeField,
        RcvDurationField,
        RcvEnumField,
        RcvFilterField,
        RcvFloatField,
        RcvFloatListField,
        RcvFormattedField,
        RcvIntField,
        RcvIntListField,
        RcvManyToManyField,
        RcvManyToOneField,
        RcvOneToManyField,
        RcvOneToOneField,
        RcvSortField,
        RcvStringField,
        RcvStringListField,
        RcvTimeField,
    ],
    Field(discriminator="kind"),
]


class RcvPlan(BaseModel):
    """A plan for rendering a resource, record and view type.

    Attributes:
        category: The category of the resource. In most cases this will be the
            same as the value passed by the front-end.
        resource: The name of the resource. In most cases this will be the
            same as the value passed by the front-end.
        record_id: The ID of the record. In most cases this will be the
            same as the value passed by the front-end.
        view_type: The type of view that is requested. In most cases this
            will be the same as the value passed by the front-end.
        render_type: The type of renderer to use. This is a hint to the
            front-end to choose the appropriate renderer.
        fields: The fields to render.
    """

    model_config = ConfigDict(extra="forbid")

    category: str | None = None
    resource: str | None = None
    record_id: int | None = None
    view_type: str | None = None
    render_type: str
    fields: list[RcvField]
