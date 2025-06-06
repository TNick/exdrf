from datetime import date, datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Tuple,
    Union,
    cast,
)

import click
import exdrf_qt.models.fields as base_classes
from attrs import Attribute
from exdrf_gen.fs_support import (
    CategDir,
    Dir,
    FieldFile,
    File,
    ResDir,
    TopDir,
)
from jinja2.runtime import Undefined

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset
    from exdrf.field import ExField
    from exdrf.field_types.str_field import StrField
    from exdrf.resource import ExResource
    from jinja2 import Environment


def get_field_value(value) -> str:
    """Create a string representation of a value.

    We use this to insert the default value of a field in the generated code.

    Args:
        value: The value to convert.

    Returns:
        A string representation of the value.
    """
    if value is None or isinstance(value, Undefined):
        return "None"
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, date):
        return f"date({value.year}, {value.month}, {value.day})"
    if isinstance(value, datetime):
        return (
            f"datetime({value.year}, {value.month}, {value.day}, "
            f"{value.hour}, {value.minute}, {value.second})"
        )
    return f"{value}"


def d_base_ui_class(field: "ExField") -> str:
    """Get the field base class given the field type.

    Args:
        field: The field to get the base class for.

    Returns:
        The base class name for the field.
    """
    if field.type_name == "blob":
        return "DrfBlobEditor"
    elif field.type_name == "text":
        return "DrfTextEditor"
    elif field.type_name == "bool":
        return "DrfBoolEditor"
    elif field.type_name == "date-time":
        return "DrfDateTimeEditor"
    elif field.type_name == "time":
        return "DrfTimeEditor"
    elif field.type_name == "date":
        return "DrfDateEditor"
    elif field.type_name == "enum":
        return "DrfEnumEditor"
    elif field.type_name == "float":
        return "DrfRealEditor"
    elif field.type_name == "integer":
        return "DrfIntEditor"
    elif field.type_name == "string":
        return (
            "DrfTextEditor"
            if cast("StrField", field).multiline
            else "DrfLineEditor"
        )
    elif field.type_name == "formatted":
        return "DrfTextEditor"
    elif field.type_name == "one-to-many":
        return f"Qt{field.ref.pascal_case_name}MuSe"  # type: ignore
    elif field.type_name == "many-to-many":
        return f"Qt{field.ref.pascal_case_name}MuSe"  # type: ignore
    elif field.type_name == "one-to-one":
        return f"Qt{field.ref.pascal_case_name}SiSe"  # type: ignore
    elif field.type_name == "many-to-one":
        return f"Qt{field.ref.pascal_case_name}SiSe"  # type: ignore
    else:
        raise ValueError(
            f"Unknown field type: {field.type_name} for field {field.name}"
        )
    # elif field.type_name == "string-list":
    # elif field.type_name == "int-list":
    # elif field.type_name == "float-list":


def d_sr_for_ui(dset: "ExDataset", c_res: List[str]) -> List[str]:
    """Default implementation of sorted_resources_for_ui.

    Args:
        dset: The dataset to generate the code for.
        c_res: The list of resource names to sort.

    Returns:
        A list of resource names sorted for UI presentation.
    """
    return sorted(c_res)


def d_sf_for_ui(
    dset: "ExDataset", res: "ExResource", fields: List[Union["ExField", str]]
) -> List[Union["ExField", str]]:
    """Default implementation of sorted_fields_for_ui.

    The default implementation returns the fields unmodified, as the fields
    will have been already sorted by the `ExResource.sorted_fields()` using
    the `ExResource.field_sort_key()` method.

    Args:
        dset: The dataset to generate the code for.
        res: The resource to generate the code for.
        fields: The list of fields to sort.

    Returns:
        A list of fields sorted for UI presentation.
    """
    return fields


def d_fld_category(field: "ExField") -> str:
    """Default implementation of set_default_fld_category.

    Args:
        field: The field to get the category for.

    Returns:
        The category for the field.
    """
    return field.category


def generate_qt_from_alchemy(
    d_set: "ExDataset",
    out_path: str,
    out_module: str,
    db_module: str,
    env: "Environment",
    sr_for_ui: Callable[["ExDataset", Any], List[str]] = d_sr_for_ui,
    sf_for_ui: Callable[
        ["ExDataset", "ExResource", List[Union["ExField", str]]],
        List[Union["ExField", str]],
    ] = d_sf_for_ui,
    base_ui_class: Callable[["ExField"], str] = d_base_ui_class,
    set_fld_category: Callable[["ExField"], str] = d_fld_category,
    **kwargs: Any,
):
    """Generate Qt widgets and models from SqlAlchemy models.

    Arguments:
        DATASET: The base class for the SQLAlchemy models as a module.name:path.
        OUT-PATH: The directory path to write the generated files to.
        OUT-MODULE: The module name to use for the generated files.
        DB-MODULE: The module name for the SQLAlchemy models.
    """
    click.echo("Generating Qt from exdrf...")

    # Allow the caller to update field categories.
    for res in d_set.resources:
        for fld in res.fields:
            fld.category = set_fld_category(fld)

    def get_changed_parts(
        field: "ExField", fld_attrs: Dict[str, Any], fld_base_class: str
    ) -> Generator[Tuple[str, str, Any], None, None]:
        # Get the base class name.
        model = getattr(base_classes, f"Qt{fld_base_class}Field")

        # Go to the properties of this field definition.
        for part in model.__attrs_attrs__:
            part = cast("Attribute", part)
            if part.name not in (
                "src",
                "ctx",
                "resource",
                "name",
                "title",
                "description",
                "ref",
                "ref_intermediate",
                "formatter",
                "fk_to",
                "fk_from",
            ):
                type_name = part.type.__name__  # type: ignore
                if type_name == "List":
                    type_name = (
                        "List["
                        + part.type.__args__[0].__name__  # type: ignore
                        + "]"
                    )
                new_value = fld_attrs.get(part.name, None)
                default_value = part.default
                if new_value != default_value:
                    yield (
                        part.name,
                        type_name,
                        get_field_value(
                            new_value
                            if new_value is not None
                            else default_value
                        ),
                    )

    def enum_values_to_prop(values: Any) -> str:
        return ",".join((str(a) + ":" + str(b)) for a, b in values)

    generator = TopDir(
        comp=[
            File("menus.py", "menus.py.j2"),
            File("router.py", "router.py.j2"),
            CategDir(
                name="{category_snake}",
                comp=[
                    File("__init__.py", "__init__.py.j2"),
                    File("api.py", "c/api.py.j2"),
                    ResDir(
                        name="{res_p_snake}",
                        comp=[
                            File("__init__.py", "__init__.py.j2"),
                            File("api.py", "c/m/api.py.j2"),
                            Dir(
                                name="fields",
                                comp=[
                                    File("__init__.py", "__init__.py.j2"),
                                    File("single_f.py", "c/m/single_f.py.j2"),
                                    FieldFile(
                                        "fld_{fld_snake}.py",
                                        "c/m/field.py.j2",
                                        extra={
                                            "gfp": get_changed_parts,
                                        },
                                    ),
                                ],
                            ),
                            Dir(
                                name="models",
                                comp=[
                                    File("__init__.py", "__init__.py.j2"),
                                    File(
                                        "{res_snake}_ful.py", "c/m/m_ful.py.j2"
                                    ),
                                    File(
                                        "{res_snake}_ocm.py", "c/m/m_ocm.py.j2"
                                    ),
                                ],
                            ),
                            Dir(
                                name="widgets",
                                comp=[
                                    File("__init__.py", "__init__.py.j2"),
                                    File(
                                        "{res_snake}_editor.py",
                                        "c/m/w/editor.py.j2",
                                    ),
                                    File(
                                        "{res_snake}_editor.ui",
                                        "c/m/w/editor.ui.j2",
                                        extra={
                                            "base_ui_class": base_ui_class,
                                            "enum_v2p": enum_values_to_prop,
                                        },
                                    ),
                                    File(
                                        "{res_snake}_selector.py",
                                        "c/m/w/selector.py.j2",
                                    ),
                                    File(
                                        "{res_snake}_list.py",
                                        "c/m/w/list.py.j2",
                                    ),
                                    File(
                                        "{res_snake}_tv.py",
                                        "c/m/w/templ_viewer.py.j2",
                                    ),
                                    File(
                                        "{res_snake}_tv.html.j2",
                                        "c/m/w/view_templ.html.j2",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
    generator.generate(
        dset=d_set,
        env=env,
        out_path=out_path,
        source_module=__name__,
        out_module=out_module,
        db_module=db_module,
        sorted_resources_for_ui=sr_for_ui,
        sorted_fields_for_ui=sf_for_ui,
        **kwargs,
    )
