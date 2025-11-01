import logging
import re
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type, cast

from attrs import define, field
from exdrf.api import (
    BlobField,
    BlobInfo,
    BoolField,
    BoolInfo,
    DateField,
    DateInfo,
    DateTimeField,
    DateTimeInfo,
    EnumField,
    EnumInfo,
    FloatField,
    FloatInfo,
    FormattedField,
    FormattedInfo,
    IntField,
    IntInfo,
    RefManyToManyField,
    RefManyToOneField,
    RefOneToManyField,
    RefOneToOneField,
    RelExtraInfo,
    StrField,
    StrInfo,
    TimeField,
    TimeInfo,
)
from exdrf.constants import RelType

from exdrf_al.visitor import DbVisitor

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset
    from exdrf.field import ExField, FieldInfo
    from exdrf.resource import ExResource
    from sqlalchemy.orm.relationships import RelationshipProperty  # noqa: F401
    from sqlalchemy.sql.elements import KeyedColumnElement  # noqa: F401

    from exdrf_al.base import Base

logger = logging.getLogger(__name__)


def res_by_table_name(dataset: "ExDataset", table_name: str) -> "ExResource":
    """Get a resource by its table name.

    When constructing the dataset from sqlalchemy the src attribute of the
    resource contains the original ORM class. The table name can be
    retrieved from the class using the `__tablename__` attribute.

    Args:
        dataset: The dataset to search in.
        table_name: The table name to search for.
    """
    results = []
    for model in dataset.resources:
        if hasattr(model.src, "__tablename__"):
            if model.src.__tablename__ == table_name:
                results.append(model)

    if len(results) == 1:
        return results[0]
    elif len(results) > 1:
        raise ValueError(
            f"Multiple resources found for table name: {table_name}"
        )
    else:
        raise KeyError(f"No resource found for table name: {table_name}")


def construct_enum(src: "KeyedColumnElement[Any]", **kwargs):
    """Construct an enum from the SQLAlchemy column.

    We need to intercept this call so that we populate the enum.
    """
    kwargs.pop("enum_values", None)
    return EnumField(
        src=src,
        enum_values=[(a, a.title()) for a in src.type.enums],  # type: ignore
        **kwargs,
    )


def sql_col_to_type(
    column: "KeyedColumnElement[Any]", extra: Dict[str, Any]
) -> Tuple[type["ExField"], type["FieldInfo"]]:
    """Select the type of the field and information parser from the SQLAlchemy
    column.

    Args:
        column: The SQLAlchemy column to convert.
        extra: Extra information to pass to the field constructor.
    """
    str_type = str(column.type)

    if (
        hasattr(column.type, "native_enum")
        and getattr(column.type, "native_enum", False) is True
        and hasattr(column.type, "enums")
        and isinstance(getattr(column.type, "enums", None), (list, tuple))
    ):
        result = construct_enum, EnumInfo
    elif str_type == "BLOB":
        result = BlobField, BlobInfo  # type: ignore
    elif str_type == "INTEGER":
        result = IntField, IntInfo  # type: ignore
    elif str_type == "TEXT":
        result = StrField, StrInfo  # type: ignore
    elif str_type == "FLOAT":
        result = FloatField, FloatInfo  # type: ignore
    elif str_type == "BOOLEAN":
        result = BoolField, BoolInfo  # type: ignore
    elif str_type == "DATE":
        result = DateField, DateInfo  # type: ignore
    elif str_type == "TIME":
        result = TimeField, TimeInfo  # type: ignore
    elif str_type == "DATETIME":
        result = DateTimeField, DateTimeInfo  # type: ignore
    elif str_type == "VARCHAR":
        result = StrField, StrInfo  # type: ignore
    elif str_type == "JSON":
        extra["format"] = "json"
        result = FormattedField, FormattedInfo  # type: ignore
    else:
        varchar_m = re.match(r"VARCHAR\((\d+)\)", str_type)
        if varchar_m:
            max_len = int(varchar_m.group(1))
            extra["max_length"] = max_len
            result = StrField, StrInfo  # type: ignore
        else:
            assert False, f"Unknown field type: {column} / {column.type}"
    return cast(Tuple[type["ExField"], type["FieldInfo"]], result)


def field_from_sql_col(
    resource: "ExResource",
    column: "KeyedColumnElement[Any]",
    **kwargs: Any,
) -> "ExField":
    """Create a field object from a SQLAlchemy column.

    Args:
        resource: The resource to which the field belongs.
        column: The SQLAlchemy column to convert.
        **kwargs: Additional arguments to pass to the Field constructor.
    """
    extra = {
        "resource": resource,
        "src": column,
        "name": column.key,
        "title": column.key.replace("_", " ").title(),
        "description": column.doc,
        "nullable": column.nullable,
        "primary": column.primary_key,
    }

    # Determine the type of the field.
    Ctor, Parser = sql_col_to_type(column, kwargs)

    # Validate the extra information from the column's info attribute.
    parsed_info = Parser.model_validate(column.info, strict=True)

    # Update extra with non-None values from extra info.
    for key, value in parsed_info.model_dump().items():
        if value is not None:
            extra[key] = value

    # Construct the field instance.
    final_args = {
        **extra,
        **kwargs,
    }
    logger.debug(
        "Creating field %s for %s.%s", Ctor.__name__, resource.name, column
    )
    result = Ctor(**final_args)

    # The field is added to the resource.
    resource.add_field(result)
    return result


def field_from_sql_rel(
    resource: "ExResource",
    relation: "RelationshipProperty",
    **kwargs: Any,
) -> "ExField":
    """Create a field object from a SQLAlchemy relationship.

    Args:
        resource: The resource to which the field belongs.
        relation: The SQLAlchemy relationship to convert.
        **kwargs: Additional arguments to pass to the Field constructor.
    """
    parsed_info = RelExtraInfo.model_validate(relation.info, strict=True)

    extra = {
        "resource": resource,
        "src": relation,
        "name": relation.key,
        "title": relation.key.replace("_", " ").title(),
    }
    # Update extra with non-None values from got_back
    for key, value in parsed_info.model_dump().items():
        if value is not None:
            extra[key] = value

    # Get the direction of the relationship.
    assert "direction" in extra, (
        "Direction must be specified for all relationships; "
        f"missing in {resource.name}.{relation.key}"
    )
    in_dir: RelType = cast(RelType, extra["direction"])
    del extra["direction"]

    # Select the correct field class based on the direction.
    Ctor: Optional[type["ExField"]] = None
    if in_dir == "OneToMany":
        Ctor = RefOneToManyField
        extra["subordinate"] = parsed_info.subordinate
    elif in_dir == "OneToOne":
        Ctor = RefOneToOneField
        extra["subordinate"] = parsed_info.subordinate
    elif in_dir == "ManyToMany":
        Ctor = RefManyToManyField
        extra["ref_intermediate"] = res_by_table_name(
            resource.dataset, getattr(relation.secondary, "key")
        )
    elif in_dir == "ManyToOne":
        Ctor = RefManyToOneField
    else:
        raise ValueError(
            f"Invalid dir: {in_dir}; expected OneToMany, ManyToOne, "
            f"OneToOne or ManyToMany in {resource.name}.{relation.key}"
        )

    # Check the correct use of the `is_list` argument.
    if in_dir in ("OneToMany", "ManyToMany"):
        assert relation.uselist, (
            f"Invalid use of `uselist` in {resource.name}.{relation.key}; "
            f"expected True for {in_dir}"
        )
        is_list = True
    else:
        assert not relation.uselist, (
            f"Invalid use of `uselist` in {resource.name}.{relation.key}; "
            f"expected False for {in_dir}"
        )
        is_list = False

    # Create the field instance.
    result = Ctor(
        ref=resource.dataset[relation.mapper.class_.__name__],
        is_list=is_list,
        **extra,  # type: ignore
        **kwargs,
    )

    # Tie fk_to and fk_from.
    fk_candidates = [
        resource[a.key]  # type: ignore
        for a in relation.local_columns
        if a.key != "id"
        # if not resource[a.key].primary  # type: ignore
    ]
    if len(fk_candidates) == 1:
        result.fk_from = fk_candidates[0]
        fk_candidates[0].fk_to = result

    resource.add_field(result)

    return result


def dataset_from_sqlalchemy(
    d_set: "ExDataset", base: Optional[Type["Base"]] = None
) -> "ExDataset":
    """Create a dataset from a SQLAlchemy database.

    Args:
        d_set: The dataset to populate.

    Returns:
        The populated dataset.
    """
    models_by_name: Dict[str, "ExResource"] = {}
    ResClass: Type["ExResource"] = d_set.res_class

    @define
    class Visitor(DbVisitor):
        res: "ExResource" = field(default=None, init=False)

        def visit_model(self, model: Type["Base"]) -> None:
            # Get the docstring and format it.
            _, doc_lines = self.get_docs(model)

            extra_info = self.extra_info(model)
            try:
                label_ast = extra_info.get_layer_ast()
            except Exception as e:
                raise ValueError(
                    f"Error parsing label for {model.__name__}"
                ) from e

            # Create a Resource object for the model.
            rs = ResClass(
                src=model,
                dataset=d_set,
                name=model.__name__,
                categories=self.category(model),
                description="\n".join(doc_lines),
                label_ast=label_ast,
            )
            self.res = rs
            models_by_name[rs.name] = rs

            # Add the resource to the dataset.
            d_set.add_resource(rs)

        def visit_column(
            self,
            model: Type["Base"],
            column: "KeyedColumnElement[Any]",
        ) -> None:
            field_from_sql_col(resource=self.res, column=column)

    @define
    class VisitorRel(DbVisitor):
        def visit_relation(
            self, model: Type["Base"], relation: "RelationshipProperty"
        ) -> None:
            res = models_by_name[model.__name__]
            field_from_sql_rel(resource=res, relation=relation)

    # Iterate all models and create resources and fields for columns.
    Visitor.run(base=base)

    # Iterate again to create fields from resources.
    VisitorRel.run(base=base)

    return d_set
