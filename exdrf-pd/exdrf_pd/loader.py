import re
from datetime import date, datetime
from typing import (
    TYPE_CHECKING,
    Any,
    ForwardRef,
    Optional,
    get_args,
    get_origin,
)

from annotated_types import Ge, Gt, Le, Lt, MaxLen, MinLen
from attrs import define

try:
    from pydantic.functional_validators import (
        AfterValidator,
        BeforeValidator,
        PlainValidator,
        WrapValidator,
    )

    _PYDANTIC_METADATA_SKIP_TYPES: tuple[type[Any], ...] = (
        BeforeValidator,
        AfterValidator,
        PlainValidator,
        WrapValidator,
    )
except ImportError:  # pragma: no cover - older pydantic
    _PYDANTIC_METADATA_SKIP_TYPES = ()
from exdrf.api import (
    BoolField,
    DateField,
    DateTimeField,
    EnumField,
    FloatField,
    FloatListField,
    IntField,
    IntListField,
    RefOneToManyField,
    RefOneToOneField,
    StrField,
    StrListField,
)

from exdrf_pd.visitor import ExModelVisitor

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset
    from exdrf.field import ExField
    from exdrf.resource import ExResource
    from pydantic.fields import FieldInfo as PdFieldInfo  # noqa: F401


def _optional_inner_type(annotation: Any) -> Any | None:
    """Return ``T`` when ``annotation`` is ``Optional[T]`` or ``T | None``.

    Args:
        annotation: A typing annotation (e.g. from ``FieldInfo.annotation``).

    Returns:
        The non-``None`` member for a plain optional union; ``None`` if the
        annotation is not exactly one non-``None`` type plus ``None``.
    """

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is None or not args:
        return None
    if type(None) not in args:
        return None
    non_none = [a for a in args if a is not type(None)]
    if len(non_none) != 1:
        return None
    return non_none[0]


def _exmodel_by_name() -> dict[str, type]:
    """Map ``ExModel`` subclass simple names to their class objects.

    Returns:
        A dictionary keyed by :attr:`type.__name__` for every registered
        :class:`exdrf_pd.base.ExModel` subclass.
    """

    from exdrf_pd.base import ExModel

    return {cls.__name__: cls for cls in ExModel.get_subclasses()}


def _is_exmodel_type(tp: Any) -> bool:
    """Return whether ``tp`` is a concrete :class:`exdrf_pd.base.ExModel` type.

    Args:
        tp: Candidate type object.

    Returns:
        ``True`` when ``tp`` is a class derived from :class:`exdrf_pd.base.ExModel`.
    """

    from exdrf_pd.base import ExModel

    try:
        return isinstance(tp, type) and issubclass(tp, ExModel)
    except TypeError:
        return False


def _paged_list_item_type(annotation: Any) -> Any | None:
    """Return the item type for a concrete ``PagedList[T]`` annotation.

    Args:
        annotation: A specialized :class:`exdrf_pd.paged.PagedList` model class.

    Returns:
        ``T`` when ``annotation`` is ``PagedList[T]``; ``None`` otherwise.
    """

    meta = getattr(annotation, "__pydantic_generic_metadata__", None)
    if not isinstance(meta, dict):
        return None
    from exdrf_pd.paged import PagedList

    if meta.get("origin") is not PagedList:
        return None
    args = meta.get("args") or ()
    if len(args) != 1:
        return None
    return args[0]


def _parse_forward_ref_arg(
    expr: str,
    models_by_name: dict[str, type],
) -> Any | None:
    """Turn a :class:`typing.ForwardRef` argument string into a live annotation.

    Args:
        expr: The forward reference's ``__forward_arg__`` text.
        models_by_name: Map of :class:`exdrf_pd.base.ExModel` names to classes.

    Returns:
        A concrete annotation suitable for :func:`field_from_pydantic`, or
        ``None`` when the expression is not supported.
    """

    from exdrf_pd.paged import PagedList

    expr = expr.strip()
    if expr.endswith(" | None"):
        inner_expr = expr[: -len(" | None")].strip()
        inner = _parse_forward_ref_arg(inner_expr, models_by_name)
        if inner is None:
            return None
        return inner | type(None)

    m = re.fullmatch(r"PagedList\[(\w+)\]", expr)
    if m:
        inner_cls = models_by_name.get(m.group(1))
        if inner_cls is None:
            return None
        return PagedList[inner_cls]

    return models_by_name.get(expr)


def _resolve_forward_ref_annotation(annotation: ForwardRef) -> Any | None:
    """Resolve a :class:`typing.ForwardRef` using registered ``ExModel`` names.

    Args:
        annotation: Pydantic field annotation that is still a forward ref.

    Returns:
        Evaluated annotation, or ``None`` if it cannot be resolved here.
    """

    raw = getattr(annotation, "__forward_arg__", None)
    if raw is None:
        return None
    return _parse_forward_ref_arg(str(raw), _exmodel_by_name())


def field_from_pydantic(
    resource: "ExResource",
    field_name,
    src_field: "PdFieldInfo",
    annotation: Optional[type] = None,
    **kwargs: Any,
) -> "ExField":
    """Create a Field object from a Pydantic field.

    Args:
        field_name: The name of the field.
        src_field: The source field.
        annotation: The type of the field; this is used when called
            recursively to create a field from a list of fields. If
            not provided the annotation of the source field is used.
        **kwargs: Additional arguments to pass to the Field constructor.

    Returns:
        The internal representation of the field.
    """
    # ds = resource.dataset
    extra = {
        "resource": resource,
        "src": src_field,
        "name": field_name,
        "title": src_field.title or field_name.replace("_", " ").title(),
        "description": src_field.description,
        **kwargs,
    }
    if annotation is None:
        annotation = src_field.annotation

    # Iterate field metadata keys and extract the information that we
    # understand.
    for md in src_field.metadata:
        if isinstance(md, MinLen):
            extra["min_length"] = md.min_length
        elif isinstance(md, MaxLen):
            extra["max_length"] = md.max_length
        elif isinstance(md, Gt):
            extra["min"] = md.gt
        elif isinstance(md, Ge):
            extra["min"] = md.ge
        elif isinstance(md, Lt):
            extra["max"] = md.lt
        elif isinstance(md, Le):
            extra["max"] = md.le
        elif _PYDANTIC_METADATA_SKIP_TYPES and isinstance(
            md,
            _PYDANTIC_METADATA_SKIP_TYPES,
        ):
            continue
        else:
            raise ValueError(f"Unknown metadata type: {md}")

    inner_opt = _optional_inner_type(annotation)
    if inner_opt is not None:
        return field_from_pydantic(
            resource,
            field_name,
            src_field,
            annotation=inner_opt,
            nullable=True,
            **kwargs,
        )

    paged_item = _paged_list_item_type(annotation)
    if paged_item is not None and _is_exmodel_type(paged_item):
        ds = resource.dataset
        result = RefOneToManyField(
            ref=ds[paged_item.__name__],
            expect_lots=True,
            **extra,
        )
        resource.add_field(result)
        return result

    if _is_exmodel_type(annotation):
        ds = resource.dataset
        result = RefOneToOneField(
            ref=ds[annotation.__name__],
            **extra,
        )
        resource.add_field(result)
        return result

    if annotation == bool:
        result = BoolField(
            **extra,
        )
    elif annotation == str:
        result = StrField(
            **extra,
        )
    elif annotation == int:
        result = IntField(
            **extra,
        )
    elif annotation == float:
        result = FloatField(
            **extra,
        )
    elif annotation is datetime:
        result = DateTimeField(
            **extra,
        )
    elif annotation is date:
        result = DateField(
            **extra,
        )
    elif annotation is Any:
        result = StrField(
            **extra,
        )
    elif str(annotation).startswith("typing.Literal["):
        values = annotation.__args__  # type: ignore
        result = EnumField(
            enum_values=[(a, a.title()) for a in values],
            **extra,
        )
    elif get_origin(annotation) is list:
        # Homogeneous ``list[T]`` / ``List[T]`` (Pydantic v2 uses ``list[int]``).
        result = None
        args = get_args(annotation)
        if len(args) == 1:
            referenced = args[0]
            if isinstance(referenced, ForwardRef):
                pass
            elif referenced is str:
                result = StrListField(
                    **extra,
                )
            elif referenced is int:
                result = IntListField(
                    **extra,
                )
            elif referenced is float:
                result = FloatListField(
                    **extra,
                )

        if result is None:
            # Composite lists (for example ``list[dict[str, Any]]`` relation key
            # payloads): use a string scalar exdrf field for metadata, but keep
            # the original pydantic ``FieldInfo`` as ``src`` so ``m2ts`` can read
            # ``field.src.annotation`` when emitting TypeScript.
            result = StrField(
                **extra,
            )
    elif isinstance(annotation, ForwardRef):
        resolved = _resolve_forward_ref_annotation(annotation)
        if resolved is not None:
            return field_from_pydantic(
                resource,
                field_name,
                src_field,
                annotation=resolved,
                **kwargs,
            )
        raise NotImplementedError(
            "Unsupported forward reference: %r" % (annotation.__forward_arg__,)
        )
    elif str(annotation).startswith("<class 'exdrf_models."):
        c_path = str(annotation)[8:-2]
        _, cls_name = c_path.rsplit(".", 1)
        raise NotImplementedError
        # result = RefManyField(
        #     ref=ds[cls_name],
        #     **extra,
        # )
    # elif field_name == "filter":
    #     result = FilterField(
    #         **extra,
    #     )
    else:
        assert False, f"Unknown field type: {annotation}"

    resource.add_field(result)
    return result


def dataset_from_pydantic(d_set: "ExDataset") -> "ExDataset":
    """Create a dataset from a SQLAlchemy database.

    Args:
        d_set: The dataset to populate.

    Returns:
        The populated dataset.
    """
    ResClass = d_set.res_class

    @define
    class Visitor(ExModelVisitor):
        """A visitor that simply creates one resource for each model."""

        def visit_model(self, model, name, categories):
            # Get the docstring and format it.
            _, doc_lines = self.get_docs(model)

            # Create a Resource object for the model.
            rs = ResClass(
                src=model,
                dataset=d_set,
                name=name,
                categories=categories,
                description="\n".join(doc_lines),
            )

            # Add the resource to the dataset.
            d_set.resources.append(rs)

    # Iterate all modes that inherit from ExModel and create a resource
    # for each of them.
    v = Visitor.run()

    # The visitor also creates a map of categories to models.
    d_set.category_map = v.categ_map

    # Retrieve fields from the models and create a Field object for each
    # field in the resource.
    for resource in d_set.resources:
        # TODO:
        # if resource.name in ("ListResponse", "ListRequest"):
        #     continue

        # Get a list of fields sorted by name, but with the id
        # field first.
        fields = sorted(
            ((a, b) for a, b in resource.src.model_fields.items()),
            key=lambda x: x[0] if x[0] != "id" else "",
        )

        # Create a Field object for each field in the resource.
        for field_name, src_field in fields:
            field_from_pydantic(resource, field_name, src_field)

    return d_set
