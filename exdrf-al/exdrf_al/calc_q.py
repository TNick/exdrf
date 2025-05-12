from typing import List, Optional, Union, cast

from attrs import define, field
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

    def stringify(
        self,
        indent: int = 12,
        level: int = 0,
        lines: Optional[List[str]] = None,
        parents: Optional[List["JoinLoad"]] = None,
    ) -> str:
        if parents is None:
            parents = []
        if lines is None:
            lines = []

        s_indent_1 = " " * (indent + 4)
        s_indent_2 = " " * (indent + 8)

        if self.load_only:
            for i_p, parent in enumerate(parents):
                dot = "" if i_p == 0 else "."
                st = parent.container.strategy
                lines.append(
                    f"{s_indent_1}{dot}{st}(Db{repr(parent.container)})"
                )
            dot = "." if parents else ""
            st = self.container.strategy
            lines.append(f"{s_indent_1}{dot}{st}(Db{repr(self.container)})")
            lines.append(f"{s_indent_1}.load_only(")
            for lo in self.load_only:
                lines.append(f"{s_indent_2}Db{repr(lo)},")
            lines.append(f"{s_indent_1}),")

        for c in self.children:
            c.stringify(
                indent=indent,
                level=level + 1,
                lines=lines,
                parents=parents + [self],
            )

        return "\n".join(lines) if level == 0 else ""

    def load(self, sub_fld_name: str, related_model: "ExResource"):
        """Add a field to the tree.

        Args:
            sub_fld_name: The name of the field to load, in dot notation.
            related_model: The model that contains the first part of the name
                (the first model in the chain).
        """
        parts = sub_fld_name.split(".")

        # The parts up to but excluding last one generate joins, the
        # last one generates a load_only.
        crt_join = self
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


@define
class RootJoinLoad(JoinLoad):
    def stringify(
        self,
        indent: int = 12,
        level: int = 0,
        lines: Optional[List[str]] = None,
        parents: Optional[List["JoinLoad"]] = None,
    ) -> str:
        s_indent_1 = " " * (indent + 4)
        s_indent_2 = " " * (indent + 8)
        result = s_indent_1 + "load_only(\n"
        for lo in self.load_only:
            result += s_indent_2 + "Db" + repr(lo) + ",\n"
        return result + s_indent_1 + ")\n"


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

        # Go through all the fields required by this related model to
        # 1) identify a record (primary keys) and 2) be able to construct
        # a label for that record.
        # This is a flat list and nested fields are represented using
        # the dot notation, so there's no need for recursion.
        for sub_fld_name in fld.ref.minimum_field_set():
            top_join.load(sub_fld_name, fld.ref)

    return result


def all_related_models(model: "ExResource"):
    result = list()
    for jn in all_related_paths(model):
        jn.collect_resources(result)

    # Deduplicate the result based on the resource name
    return sorted(
        {res.name: res for res in result}.values(), key=lambda x: x.name
    )


def all_related_label_paths(model: "ExResource"):
    result = []

    root_join = RootJoinLoad(
        container=FieldRef(resource=model, name=model.name, is_list=False),
    )
    result.append(root_join)

    top_parts = {}

    # Go through all the fields that point to other resources
    for f_name in model.minimum_field_set():
        parts = f_name.split(".")
        if len(parts) > 1:

            # This is the reference to the related model in the source model.
            fld = model[parts[0]]
            top_join = top_parts.get(parts[0])
            if top_join is None:
                top_join = JoinLoad(
                    container=FieldRef(
                        resource=model, name=parts[0], is_list=fld.is_list
                    ),
                )
                result.append(top_join)

            assert isinstance(
                fld, RefBaseField
            ), f"Field {fld} is not a reference field"
            for sub_fld_name in fld.ref.minimum_field_set():
                top_join.load(sub_fld_name, fld.ref)

        else:
            root_join.load_only.append(
                FieldRef(
                    resource=model,
                    name=f_name,
                    is_list=False,
                )
            )

    return result


def all_related_label_models(model: "ExResource"):
    result = list()
    for jn in all_related_label_paths(model):
        jn.collect_resources(result)

    # Deduplicate the result based on the resource name
    return sorted(
        {res.name: res for res in result}.values(), key=lambda x: x.name
    )
