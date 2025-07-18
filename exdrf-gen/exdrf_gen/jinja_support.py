import importlib
import json
import logging
import math
import os
import re
from datetime import datetime
from os.path import getmtime, isfile, join
from typing import Any

from exdrf.utils import inflect_e
from jinja2 import (
    BaseLoader,
    Environment,
    TemplateNotFound,
    Undefined,
    select_autoescape,
)

logger = logging.getLogger(__name__)


class Loader(BaseLoader):
    """Jinja loader that loads templates from a set of paths."""

    def __init__(self, path):
        self.paths = []

    def get_source(self, environment, template):
        if isfile(template):
            template_path = template
        else:
            template_path = None
            for path in self.paths:
                candidate_path = join(path, *template.split("/"))
                if isfile(candidate_path):
                    template_path = candidate_path
                    break

            # Attempt to treat it like a module name.
            if template_path is None:
                m_parts = template.split("/")
                m_path = ".".join(m_parts[:-1])
                m_name = m_parts[-1]
                try:
                    # "exdrf_dev.db.tags.widgets"
                    module = importlib.import_module(m_path)
                    module_file = getattr(module, "__file__", None)
                    if module_file is not None:
                        template_path = join(
                            os.path.dirname(module_file), m_name
                        )
                        if not isfile(template_path):
                            template_path = template_path + ".j2"
                            if not isfile(template_path):
                                template_path = None
                except Exception as e:
                    logger.warning(
                        f"Failed to treat {template} as a module: {e}"
                    )

        # If the template is not found in any of these paths, raise an error
        if template_path is None:
            raise TemplateNotFound(template)

        # Store the last modified time of the template file
        mtime = getmtime(template_path)

        # Read the template file
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception:
            with open(template_path, "r") as f:
                source = f.read()

        # Return the source, template path, and a function to check if the
        # template has changed
        return source, template_path, lambda: mtime == getmtime(template_path)


def jinja_round(value, precision=0, method="common"):
    import math

    s_value = repr(value)
    if s_value.startswith("Markup('") and s_value.endswith("')"):
        value = float(s_value[8:-2])

    if method == "common":
        try:
            return round(value, precision)
        except Exception:
            return value
    elif method == "ceil":
        factor = 10**precision
        return math.ceil(value * factor) / factor
    elif method == "floor":
        factor = 10**precision
        return math.floor(value * factor) / factor
    else:
        raise ValueError("method must be 'common', 'ceil', or 'floor'")


def jinja_length(value):
    return len(value)


def jinja_list(value):
    return list(value)


def jinja_range(*args):
    return list(range(*args))


def jinja_format(value, *args, **kwargs):
    # Accepts both old-style and new-style formatting
    if isinstance(value, str):
        if args and ("{" in value and "}" in value):
            return value.format(*args, **kwargs)
        else:
            return value % args if args else value
    return value


def jinja_sorted(value, key=None, reverse=False):
    if key is not None:
        return sorted(value, key=lambda x: getattr(x, key), reverse=reverse)
    else:
        return sorted(value, reverse=reverse)


def jinja_sorted_k(value, key=None, reverse=False):
    if key is not None:
        return sorted(value, key=lambda x: x[key], reverse=reverse)
    else:
        return sorted(value, reverse=reverse)


def jinja_equals(target_list, key, value):
    return list(item for item in target_list if getattr(item, key) == value)


def jinja_not_equals(target_list, key, value):
    return list(item for item in target_list if getattr(item, key) != value)


def jinja_contains(target_list, key, value):
    return any(getattr(item, key) == value for item in target_list)


def jinja_format_date(date, format_string="%d-%m-%Y"):
    if date is None:
        return "-"
    return date.strftime(format_string)


def join_non_empty(sep: str = ",", *args: Any) -> str:
    """Join a list of strings, ignoring empty strings.

    Empty strings are:
        - strings with length 0,
        - None values,
        - Jinja undefined values.

    Args:
        sep: The separator to use between the strings.
        *args: The strings to join.
    """
    return sep.join(
        arg
        for arg in args
        if arg is not None and not isinstance(arg, Undefined) and len(arg) > 0
    )


def join_attrs(
    source: Any,
    attr: str,
    sep: str = ",",
    prefix: str = "",
    suffix: str = "",
    prefix_is_attr: bool = False,
    suffix_is_attr: bool = False,
    prefix_sep: str = "",
    suffix_sep: str = "",
) -> str:
    def get_item(s: Any) -> str:
        _prefix = getattr(s, prefix) if prefix_is_attr else prefix
        _suffix = getattr(s, suffix) if suffix_is_attr else suffix
        return (
            _prefix + prefix_sep + str(getattr(s, attr)) + suffix_sep + _suffix
        )

    return sep.join(get_item(s) for s in source)


def view_url_for(resource: str, id: Any) -> str:
    return f"exdrf://navigation/resource/{resource}/{id}"


def list_url_for(resource: str) -> str:
    return f"exdrf://navigation/resource/{resource}"


def edit_url_for(resource: str, id: Any) -> str:
    if not isinstance(id, int):
        id = ",".join(str(i) for i in id)
    return f"exdrf://navigation/resource/{resource}/{id}/edit"


def create_url_for(resource: str) -> str:
    return f"exdrf://navigation/resource/{resource}/create"


def delete_url_for(resource: str, id: Any) -> str:
    if not isinstance(id, int):
        id = ",".join(str(i) for i in id)
    return f"exdrf://navigation/resource/{resource}/{id}/delete"


def escape_character(value: str, char: str, mode: str = "html") -> str:
    if not value:
        return value
    if mode == "html":
        if char == "'":
            return value.replace("'", "&apos;")
        elif char == '"':
            return value.replace('"', "&quot;")
        else:
            return value

    # Skip characters that are already escaped
    result = []
    i = 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value) and value[i + 1] == char:
            result.append(value[i : i + 2])  # noqa: E203
            i += 2
        elif value[i] == char:
            result.append(f"\\{char}")
            i += 1
        else:
            result.append(value[i])
            i += 1
    return "".join(result)


def to_json(
    value: Any,
    padding: int = 0,
    indent: int = 2,
    space: str = " ",
    exclude: set = set(),
) -> str:
    """Convert a value to a JSON string.

    Args:
        value: The value to convert.
        padding: The number of spaces to prepend to each line.
        indent: The number of additional spaces to add for each level of
            nesting.
        space: The space character to use for indentation. Padding and
            indent are expressed in terms of this character.
        exclude: A set of attribute names to exclude from the JSON string.
            It uses the dot notation to specify nested attributes.
    """

    def _filter_value(data: Any, exclude_set: set, parent_key: str = "") -> Any:
        if isinstance(data, dict):
            res = {}
            for key, val in data.items():
                current_key = f"{parent_key}.{key}" if parent_key else key
                if current_key in exclude_set:
                    continue
                res[key] = _filter_value(val, exclude_set, current_key)
            return res
        if isinstance(data, list):
            return [
                _filter_value(item, exclude_set, parent_key) for item in data
            ]
        return data

    if exclude:
        value = _filter_value(value, exclude)

    indent_str = space * indent if indent > 0 else None

    result = json.dumps(
        value,
        indent=indent_str,
        ensure_ascii=False,
        default=str,
    )

    if padding > 0:
        padding_str = space * padding
        lines = result.splitlines()
        padded_lines = [f"{padding_str}{line}" for line in lines]
        result = "\n".join(padded_lines)

    return result


def create_jinja_env(auto_reload=False):
    """Creates a base Jinja2 environment for rendering templates."""
    jinja_env = Environment(
        loader=Loader(os.path.dirname(__file__)),
        autoescape=select_autoescape(),
        auto_reload=auto_reload,
    )

    # List functions.
    jinja_env.globals["len"] = lambda x: len(x)
    jinja_env.globals["sorted"] = lambda x: sorted(x)
    jinja_env.globals["enumerate"] = lambda x: enumerate(x)
    jinja_env.globals["len_range"] = lambda x: range(len(x))

    # Containers.
    jinja_env.globals["list"] = list
    jinja_env.globals["set"] = set
    jinja_env.globals["dict"] = dict

    # String utilities.
    jinja_env.globals["str"] = lambda x: str(x)
    jinja_env.globals["join_non_empty"] = join_non_empty
    jinja_env.globals["proper"] = lambda x: " ".join(
        word.capitalize() for word in str(x).split()
    )
    jinja_env.globals["title"] = lambda x: x.title()
    jinja_env.globals["lower"] = lambda x: x.lower()
    jinja_env.globals["upper"] = lambda x: x.upper()
    jinja_env.globals["strip"] = lambda x: x.strip()
    jinja_env.globals["lstrip"] = lambda x: x.lstrip()
    jinja_env.globals["rstrip"] = lambda x: x.rstrip()
    jinja_env.globals["pluralize"] = lambda x: inflect_e.plural(x)
    jinja_env.globals["snake_pl"] = lambda x: inflect_e.plural(
        re.sub(r"(?<!^)(?=[A-Z])", "_", x).lower()  # type: ignore
    )
    jinja_env.globals["snake"] = lambda x: re.sub(
        r"(?<!^)(?=[A-Z])", "_", x
    ).lower()

    # Number utilities.
    jinja_env.globals["int"] = lambda x: (
        int(x) if (x is not None and x is not Undefined) else None
    )
    jinja_env.globals["format_int"] = lambda x: (
        f"{x:,.0f}" if (x is not None and x is not Undefined) else "-"
    )
    jinja_env.globals["float"] = lambda x: (
        float(x) if (x is not None and x is not Undefined) else None
    )
    jinja_env.globals["format_float"] = lambda x, y: (
        f"{x:.{y}f}" if (x is not None and x is not Undefined) else "-"
    )

    # Date utilities.
    jinja_env.globals["format_date"] = jinja_format_date
    jinja_env.globals["format_datetime"] = lambda x: (
        jinja_format_date(x, "%d-%m-%Y %H:%M:%S")
    )
    jinja_env.globals["get_now"] = lambda: datetime.now()

    # Math utilities.
    jinja_env.globals["sqrt"] = lambda x: math.sqrt(x)
    jinja_env.globals["atan2"] = lambda x, y: math.atan2(x, y)
    jinja_env.globals["min"] = lambda x, y: min(x, y)
    jinja_env.globals["max"] = lambda x, y: max(x, y)
    jinja_env.globals["abs"] = lambda x: abs(x)
    jinja_env.globals["range"] = range
    jinja_env.globals["round"] = round
    jinja_env.globals["pi"] = math.pi
    jinja_env.globals["view_url_for"] = view_url_for
    jinja_env.globals["list_url_for"] = list_url_for
    jinja_env.globals["edit_url_for"] = edit_url_for
    jinja_env.globals["create_url_for"] = create_url_for
    jinja_env.globals["delete_url_for"] = delete_url_for
    jinja_env.globals["internal_link_class"] = "exdrf-internal-link"
    jinja_env.globals["deleted_record_class"] = "exdrf-deleted-record"
    jinja_env.globals["escape_sq"] = lambda x: escape_character(x, "'")
    jinja_env.globals["escape_dq"] = lambda x: escape_character(x, '"')

    # Tests.
    jinja_env.tests["None"] = lambda value: value is None

    # Jinja filters.
    jinja_env.filters["format_int"] = lambda x: (
        f"{x:,.0f}" if (x is not None and x is not Undefined) else "-"
    )
    jinja_env.filters["format_float"] = lambda x, y: (
        f"{x:.{y}f}" if (x is not None and x is not Undefined) else "-"
    )
    jinja_env.filters["format_date"] = lambda x: (
        x.strftime("%d-%m-%Y")
        if (x is not None and x is not Undefined)
        else "-"
    )
    jinja_env.filters["format_datetime"] = lambda x: (
        x.strftime("%d-%m-%Y %H:%M:%S")
        if (x is not None and x is not Undefined)
        else "-"
    )
    jinja_env.filters["proper"] = lambda x: " ".join(
        word.capitalize() for word in str(x).split()
    )
    jinja_env.filters["join_attrs"] = join_attrs
    jinja_env.filters["title"] = lambda x: x.title()
    jinja_env.filters["round"] = jinja_round
    jinja_env.filters["length"] = jinja_length
    jinja_env.filters["list"] = jinja_list
    jinja_env.filters["format"] = jinja_format
    jinja_env.filters["range"] = jinja_range
    jinja_env.filters["sorted"] = jinja_sorted
    jinja_env.filters["sorted_k"] = jinja_sorted_k
    jinja_env.filters["equals"] = jinja_equals
    jinja_env.filters["not_equals"] = jinja_not_equals
    jinja_env.filters["contains"] = jinja_contains
    jinja_env.filters["sqrt"] = lambda x: math.sqrt(x)
    jinja_env.filters["atan2"] = lambda x, y: math.atan2(x, y)
    jinja_env.filters["min"] = lambda x, y: min(x, y)
    jinja_env.filters["max"] = lambda x, y: max(x, y)
    jinja_env.filters["abs"] = lambda x: abs(x)
    jinja_env.filters["lower"] = lambda x: x.lower()
    jinja_env.filters["upper"] = lambda x: x.upper()
    jinja_env.filters["strip"] = lambda x: x.strip()
    jinja_env.filters["lstrip"] = lambda x: x.lstrip()
    jinja_env.filters["rstrip"] = lambda x: x.rstrip()
    jinja_env.filters["escape_sq"] = lambda x: escape_character(x, "'")
    jinja_env.filters["escape_dq"] = lambda x: escape_character(x, '"')
    jinja_env.filters["pluralize"] = lambda x: inflect_e.plural(x)
    jinja_env.filters["snake_pl"] = lambda x: inflect_e.plural(
        re.sub(r"(?<!^)(?=[A-Z])", "_", x).lower()  # type: ignore
    )
    jinja_env.filters["snake"] = lambda x: re.sub(
        r"(?<!^)(?=[A-Z])", "_", x
    ).lower()
    jinja_env.filters["to_json"] = to_json
    return jinja_env


jinja_env = create_jinja_env()


def recreate_global_env():
    global jinja_env
    jinja_env = create_jinja_env(auto_reload=True)
    logger.info("Recreated Jinja environment")
    return jinja_env
