from typing import TYPE_CHECKING, Any, List

from exdrf.constants import (
    FIELD_TYPE_BLOB,
    FIELD_TYPE_BOOL,
    FIELD_TYPE_DATE,
    FIELD_TYPE_DT,
    FIELD_TYPE_DURATION,
    FIELD_TYPE_ENUM,
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
)
from exdrf_gen.fs_support import (
    CategDir,
    File,
    ResFile,
    TopDir,
)
from jinja2 import Environment

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset
    from exdrf.field import ExField
    from exdrf.resource import ExResource


_type_to_xl = {
    FIELD_TYPE_BLOB: "bytes",
    FIELD_TYPE_BOOL: "bool",
    FIELD_TYPE_DT: "datetime",
    FIELD_TYPE_DATE: "date",
    FIELD_TYPE_TIME: "time",
    FIELD_TYPE_DURATION: "timedelta",
    FIELD_TYPE_ENUM: "enum",
    FIELD_TYPE_FLOAT: "float",
    FIELD_TYPE_INTEGER: "int",
    FIELD_TYPE_STRING: "str",
    FIELD_TYPE_STRING_LIST: "list[str]",
    FIELD_TYPE_INT_LIST: "list[int]",
    FIELD_TYPE_FLOAT_LIST: "list[float]",
    FIELD_TYPE_FORMATTED: "str",
    FIELD_TYPE_SORT: "str",
    FIELD_TYPE_REF_ONE_TO_MANY: "list[str]",
    FIELD_TYPE_REF_ONE_TO_ONE: "str",
    FIELD_TYPE_REF_MANY_TO_MANY: "list[str]",
    FIELD_TYPE_REF_MANY_TO_ONE: "str",
}


def type_to_xl(type: str) -> str:
    return _type_to_xl[type]


def field_sort_key(res: "ExResource", fld: "ExField") -> str:
    """Get the sort key for a field.

    The sort key is used to sort the fields in the resource. By default it
    is computed by joining the categories of the resource with the name of
    the field.

    You may want to reimplement this method in a subclass if you want to
    the fields ranked before the alphabetical sort.

    Args:
        fld: The field to get the sort key for.

    Returns:
        The sort key for the field.
    """
    if fld.primary:
        prefix = "0"
    elif fld.name == "description":
        prefix = "7"
    elif fld.name == "deleted":
        prefix = "8"
    elif fld.name == "created_on":
        prefix = "9"
    elif fld.name == "updated_on":
        prefix = "9"
    else:
        prefix = "1"
    category = fld.category or ""
    return f"{prefix}.{category}.{fld.name}"


def sorted_fields(res: "ExResource") -> List["ExField"]:
    """Get a sorted list of fields.

    You can customize the order of the fields by reimplementing the
    `field_sort_key` method.
    """
    return sorted(
        res.fields,
        key=lambda fld: field_sort_key(res, fld),
    )


def generate_xl_from_alchemy(
    d_set: "ExDataset",
    out_path: str,
    out_module: str,
    db_module: str,
    env: "Environment",
    **kwargs: Any,
):
    # Only allow our templates to be used.
    env.loader.paths = list(
        filter(  # type: ignore
            lambda x: x.endswith("al2xl_templates"),
            env.loader.paths,  # type: ignore
        )
    )
    generator = TopDir(
        comp=[
            File("__init__.py", "__init__.py.j2"),
            File("api.py", "api.py.j2"),
            File("schema_from_text.py", "schema_from_text.py.j2"),
            CategDir(
                name="{category_snake}",
                comp=[
                    File("__init__.py", "c/__init__.py.j2"),
                    File("api.py", "c/api.py.j2"),
                    ResFile(
                        name="{res_snake}.py",
                        template="c/m.py.j2",
                    ),
                ],
            ),
        ]
    )
    generator.generate(
        dset=d_set,
        env=env,
        out_path=out_path,
        source_module=__name__,
        out_module=out_module,
        db_module=db_module,
        type_to_xl=type_to_xl,
        sorted_fields=sorted_fields,
        **kwargs,
    )
