from typing import TYPE_CHECKING, Any, ForwardRef, List, Optional

from annotated_types import Ge, Gt, Le, Lt, MaxLen, MinLen
from attrs import define
from exdrf.api import (
    BoolField,
    EnumField,
    FloatField,
    FloatListField,
    IntField,
    IntListField,
    StrField,
    StrListField,
)

from exdrf_pd.visitor import ExModelVisitor

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset
    from exdrf.field import ExField
    from exdrf.resource import ExResource
    from pydantic.fields import FieldInfo as PdFieldInfo  # noqa: F401


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
        else:
            raise ValueError(f"Unknown metadata type: {md}")

    if annotation == bool:
        result = BoolField(
            **extra,
        )
    if annotation == str:
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
    elif str(annotation).startswith("typing.Literal["):
        values = annotation.__args__  # type: ignore
        result = EnumField(
            enum_values=[(a, a.title()) for a in values],
            **extra,
        )
    elif isinstance(annotation, (list, List)) or str(annotation).startswith(
        "typing.List["
    ):
        # if field_name == "filter":
        #     result = FilterField(
        #         **extra,
        #     )
        # elif field_name == "sort":
        #     result = SortField(
        #         **extra,
        #     )
        # else:
        result = None
        referenced = annotation.__args__[0]  # type: ignore
        if isinstance(referenced, ForwardRef):
            pass
            # other = referenced.__forward_arg__
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
        # else:
        # s_cls = str(referenced)
        # other = referenced.__class__.__name__

        if result is None:
            # TODO: replace with the new 4-class implementation
            raise NotImplementedError
            # result = RefOneField(
            #     ref=ds[other],  # type: ignore
            #     **extra,
            # )
    elif isinstance(annotation, ForwardRef):
        # referenced = annotation
        # if isinstance(referenced, ForwardRef):
        #     other = referenced.__forward_arg__
        # else:
        #     other = referenced.__class__.__name__
        # TODO: replace with the new 4-class implementation
        raise NotImplementedError
        # result = RefManyField(
        #     ref=ds[other],
        #     **extra,
        # )
    elif str(annotation).startswith("typing.Optional["):
        return field_from_pydantic(
            resource,
            field_name,
            src_field,
            annotation=annotation.__args__[0],  # type: ignore
            **extra,
            nullable=True,
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
