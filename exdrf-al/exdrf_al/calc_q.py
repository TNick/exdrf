from typing import TYPE_CHECKING, List, Union, cast

from attrs import define, field

if TYPE_CHECKING:
    from exdrf.field_types.api import RefBaseField

from exdrf.resource import ExResource


@define
class FieldRef:
    """A simplified representation of a field that points to a resource.

    Attributes:
        resource: The resource that the field points to.
        name: The name of the ORM attribute in the source resource.
        is_list: Indicates if the relation is OneToMany or ManyToMany when True
            or OneToOne or ManyToOne when False.
    """

    resource: "ExResource"
    name: str
    is_list: bool

    def __repr__(self) -> str:
        return f"{self.res_name}.{self.name}"

    @property
    def res_name(self) -> str:
        """The name of the resource that the field points to."""
        return self.resource.name

    @property
    def strategy(self) -> str:
        """What loading strategy to use for the ORM query."""
        return "selectinload" if self.is_list else "joinedload"


@define
class JoinLoad:
    """A node in the intermediate tree structure for loading related resources.

    Attributes:

    """

    container: FieldRef
    load_only: List[FieldRef] = field(factory=list)
    children: List["JoinLoad"] = field(factory=list)

    def __repr__(self) -> str:
        return f"Join({self.container}, {self.load_only}, {len(self.children)})"

    def get_child(self, model_name, field_name) -> Union["JoinLoad", None]:
        """Locate a child given the model name and field name."""
        for child in self.children:
            if (
                child.container.res_name == model_name
                and child.container.name == field_name
            ):
                return child
        return None

    def get_join(self, model: "ExResource", field_name: str) -> "JoinLoad":
        """Retrieve the join for the given field.

        If the join does not exist, the method creates it and adds it to the
        list of children.
        """
        child = self.get_child(model.name, field_name)
        if child:
            return child

        # Create a new join and add it to the list of children.
        fld = model[field_name]
        new_join = JoinLoad(
            container=FieldRef(
                resource=model, name=field_name, is_list=fld.is_list
            ),
        )
        self.children.append(new_join)
        return new_join

    def collect_resources(self, result: List["ExResource"]):
        """Collect all the resources in this join and its children."""
        result.append(self.container.resource)
        for child in self.children:
            child.collect_resources(result)
        for lo in self.load_only:
            result.append(lo.resource)
        return result

    def stringify(self, indent: int = 12, level: int = 0) -> str:
        """Stringify the join."""
        s_indent_11 = " " * (indent + 4)
        s_indent_222 = " " * (indent + 8)
        result = (
            s_indent_11
            + (")." if level > 0 else "")
            + self.container.strategy
            + "(\n"
            + s_indent_222
            + "Db"
            + repr(self.container)
            + ",\n"
        )

        if self.load_only:
            result += s_indent_11 + ").load_only(\n"
            for lo in self.load_only:
                result += s_indent_222 + "Db" + repr(lo) + ",\n"

        if len(self.children) > 0:
            for c in self.children:
                result += c.stringify(indent=indent, level=level + 1)

        if level == 0:
            return result + s_indent_11 + ")\n"
        else:
            return result


def all_related_paths(model: "ExResource"):
    """Creates a structure that indicates how to load all the related resources.

    This is useful for constructing the ORM query to load all the related
    resources in a single query. The structure is a tree where each node
    represents a join and the children represent the related resources that
    need to be loaded. The leaves of the tree are the fields that need to be
    loaded using the load_only strategy.
    """
    result = []

    # Go through all the fields that point to other resources
    for fld in model.ref_fields:
        # This is the reference to the related model in the source model.
        top_join = JoinLoad(
            container=FieldRef(
                resource=model, name=fld.name, is_list=fld.is_list
            ),
        )
        result.append(top_join)

        # The related resource.
        related_model = fld.ref

        # Go through all the fields required by this related model to
        # 1) identify a record (primary keys) and 2) be able to construct
        # a label for that record.
        # This is a flat list and nested fields are represented using
        # the dot notation, so there's no need for recursion.
        for sub_fld_name in related_model.minimum_field_set():
            parts = sub_fld_name.split(".")

            # The parts up to but excluding last one generate joins, the
            # last one generates a load_only.
            crt_join = top_join
            crt_model = related_model
            for part in parts[:-1]:
                crt_join = crt_join.get_join(crt_model, part)
                crt_model = cast("RefBaseField", crt_model[part]).ref

            # Add the field to the load_only list of the last join.
            crt_join.load_only.append(
                FieldRef(
                    resource=crt_model,
                    name=parts[-1],
                    is_list=crt_model[parts[-1]].is_list,
                )
            )

    return result


def all_related_models(model: "ExResource"):
    result = list()
    for jn in all_related_paths(model):
        jn.collect_resources(result)

    # Deduplicate the result based on the resource name
    return sorted(
        {res.name: res for res in result}.values(), key=lambda x: x.name
    )
