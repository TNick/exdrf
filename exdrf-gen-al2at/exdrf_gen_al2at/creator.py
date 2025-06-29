from typing import TYPE_CHECKING, Any

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


_type_to_attrs = {
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


def type_to_attrs(type: str) -> str:
    return _type_to_attrs[type]


def generate_attrs_from_alchemy(
    d_set: "ExDataset",
    out_path: str,
    out_module: str,
    db_module: str,
    env: "Environment",
    **kwargs: Any,
):
    generator = TopDir(
        comp=[
            File("__init__.py", "__init__.py.j2"),
            File("api.py", "api.py.j2"),
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
        type_to_attrs=type_to_attrs,
        **kwargs,
    )
