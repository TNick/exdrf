import os
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
    Optional,
)
import logging
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

logger = logging.getLogger(__name__)


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
    read_only_fields: Dict[str, Any] = {},
    **kwargs: Any,
):
    """Generate Qt widgets and models from SqlAlchemy models.

    Args:
        d_set: The dataset to generate the code for.
        out_path: The path to write the generated files to.
        out_module: The module name to use for the generated files.
        db_module: The module name for the SQLAlchemy models.
        env: The Jinja environment to use for the generated code.
        sr_for_ui: The function to use to sort the resources for the UI.
        sf_for_ui: The function to use to sort the fields for the UI.
        base_ui_class: The function to use to get the base UI class for a field.
        set_fld_category: The function to use to set the category for a field.
        read_only_fields: The keys indicates which field names are read-only.
            The name may include a single dot, with first part representing the
            resource name and the second part representing the field name. If
            the dot is not present, the field is matched by name across all
            resources.
            The value is a dictionary that indicate how to deal with the field:
                * rec_to_str: this is a string that should accept a dingle
                  format argument called `field`; it is used to generate the
                  code that populates the editor. The default is to generate
                  `self.c_{{ field }}.setText(
                      str(record.{{ field }}) if record else ""
                  )`
                * ui_xml: this is a string that contains the XML for the field
                  in the .ui file of the editor; by default a line edit is
                  created with readOnly set to true.
        **kwargs: Additional keyword arguments to pass to the generator.
    """
    click.echo("Generating Qt from exdrf...")

    # Loader strategy policy for generated default selections.
    #
    # We default to selectinload for nested scalar relationships because it is
    # usually faster for deep graphs and avoids producing very wide joins.
    # The behavior is opt-out.
    disable_nested_scalar_selectinload = os.getenv(
        "EXDRF_AL2QT_DISABLE_SELECTINLOAD_FOR_NESTED_SCALARS", ""
    ).strip().lower() in ("1", "true", "yes")
    legacy_enable_value = os.getenv(
        "EXDRF_AL2QT_USE_SELECTINLOAD_FOR_NESTED_SCALARS", ""
    ).strip()
    if legacy_enable_value:
        # Backward-compatible override: if the legacy env var is set, respect
        # its boolean value.
        use_selectinload_for_nested_scalars = legacy_enable_value.lower() in (
            "1",
            "true",
            "yes",
        )
    else:
        use_selectinload_for_nested_scalars = (
            not disable_nested_scalar_selectinload
        )

    # Allow explicit override via kwargs (highest priority).
    if "use_selectinload_for_nested_scalars" in kwargs:
        use_selectinload_for_nested_scalars = bool(
            kwargs.pop("use_selectinload_for_nested_scalars")
        )
    # Only allow our templates to be used.
    env.loader.paths = list(  # type: ignore
        filter(  # type: ignore
            lambda x: x.endswith("al2qt_templates"),
            env.loader.paths,  # type: ignore
        )
    )

    # Allow the caller to update field categories.
    for res in d_set.resources:
        for fld in res.fields:
            fld.category = set_fld_category(fld)

            # Make sure that the read-only fields include primary keys that
            # also have a corresponding resource (editing will be done using
            # the resource).
            if fld.fk_to:
                key = res.name + "." + fld.name
                if key not in read_only_fields:
                    read_only_fields[key] = {}

    def get_changed_parts(
        field: "ExField", fld_attrs: Dict[str, Any], fld_base_class: str
    ) -> Generator[Tuple[str, str, Any], None, None]:
        logger.log(
            1,
            "Getting changed parts for field %s in resource %s",
            field.name,
            field.resource.name,
        )

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

    def parse_ro_key(
        ro_key: str, res: "ExResource"
    ) -> "Tuple[str, str, Optional[str]]":
        level_1_pair = ro_key.split(".", 1)
        if len(level_1_pair) == 2:
            res_name, rest = level_1_pair
        else:
            res_name, rest = res.name, ro_key

        level_2_pair = rest.split(":", 1)
        if len(level_2_pair) == 2:
            field_name, related_resource = level_2_pair
        else:
            field_name, related_resource = rest, None

        return res_name, field_name, related_resource

    def get_res_ro_field_data(
        res: "ExResource",
    ) -> "Dict[str, Tuple[ExField, Dict[str, Any]]]":
        result: Dict[str, Tuple[ExField, Dict[str, Any]]] = {}

        for ro_key, ro_data in read_only_fields.items():
            res_name, field_name, _ = parse_ro_key(ro_key, res)
            if res_name == res.name and field_name in res:
                field = res[field_name]
                result[field.name] = (field, ro_data)

        return result

    def get_read_only_field_data(field: "ExField") -> "Dict[str, Any] | None":
        assert field.resource is not None
        assert field.name is not None

        rr = field.related_resource

        # if field.resource.name == 'Email':
        #     breakpoint()
        candidates = []
        for ro_key, ro_data in read_only_fields.items():
            res_name, field_name, related = parse_ro_key(ro_key, field.resource)
            if res_name != field.resource.name:
                continue
            if field_name != field.name:
                continue
            explicit = ro_key.startswith(res_name)
            score = 4 if explicit else 3

            # If the definition has an explicit type only consider the related
            # resource if it is the same as the one in the field.
            if related is not None:
                if rr is not None and rr.name == related:
                    candidates.append((ro_data, score + 1))
                continue

            candidates.append((ro_data, score))
        if not candidates:
            return None
        if len(candidates) > 1:
            candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    generator = TopDir(
        comp=[
            File("menus.py", "menus.py.j2"),
            File("plugins.py", "plugins.py.j2"),
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
        read_only_fields=read_only_fields,
        get_read_only_field_data=get_read_only_field_data,
        get_res_ro_field_data=get_res_ro_field_data,
        use_selectinload_for_nested_scalars=use_selectinload_for_nested_scalars,
        **kwargs,
    )
