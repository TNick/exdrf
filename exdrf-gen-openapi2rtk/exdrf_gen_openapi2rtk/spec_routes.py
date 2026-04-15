"""Build RTK-oriented route descriptors from an OpenAPI document."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from textwrap import wrap
from typing import Any, Mapping

from exdrf_ts.json_schema_ts import json_schema_to_ts

_HTTP_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options"}
)

_REF_SCHEMA = re.compile(r"^#/components/schemas/([A-Za-z0-9_.-]+)$")

# FastAPI default ``operationId`` embeds the mounted path, e.g.
# ``list_address_generated_addresses_addresses_get``. Strip the
# ``_generated_<path>_<httpverb>`` tail so RTK keys match the handler prefix
# (``list_address`` -> ``listAddress``).
_COMPACT_FASTAPI_OPID = re.compile(
    r"^(?P<prefix>.+)_generated_[a-z0-9_]+_"
    r"(?P<verb>get|post|put|patch|delete)$",
    re.IGNORECASE,
)

_SKIP_PATH_PREFIXES = (
    "/openapi.json",
    "/docs",
    "/redoc",
    "/favicon.ico",
)


@dataclass
class GenField:
    """Single property on a JSON request body model."""

    name: str


@dataclass
class GenBodyModel:
    """Named request body schema (typically a ``$ref`` component)."""

    name: str
    fields: list[GenField] = field(default_factory=list)


@dataclass
class GenMethod:
    """HTTP verb for a synthesized route."""

    name: str


@dataclass
class GenRoute:
    """One OpenAPI operation mapped for RTK template rendering."""

    name: str
    name_snake_case: str
    name_camel: str
    name_pascal: str
    method: GenMethod
    path: str
    doc_lines: list[str]
    path_args: list[tuple[str, str]]
    query_args: list[tuple[str, str]]
    body_m: GenBodyModel | None
    body_args: list[tuple[str, str]]
    body_schema_name: str | None
    response_ts: str
    arg_type_ts: str = ""
    is_mutation: bool = False


def _snake_to_camel(name: str) -> str:
    """Convert ``snake_case`` to ``camelCase``."""

    parts = [p for p in name.split("_") if p]
    if not parts:
        return name
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def _snake_to_pascal(name: str) -> str:
    """Convert ``snake_case`` to ``PascalCase``."""

    return "".join(p.capitalize() for p in name.split("_") if p)


def _compact_operation_id_snake(snake: str) -> str:
    """Drop FastAPI's ``_generated_<route>_<verb>`` suffix when present.

    Args:
        snake: Lowercase snake_case ``operationId``.

    Returns:
        Shortened snake_case suitable for RTK endpoint keys.
    """

    m = _COMPACT_FASTAPI_OPID.match(snake)
    if m:
        return m.group("prefix").lower()
    return snake


def _operation_snake(
    operation: Mapping[str, Any],
    method: str,
    path: str,
) -> str:
    """Derive a stable snake_case name for an operation."""

    oid = operation.get("operationId")
    if isinstance(oid, str) and oid.strip():
        raw = oid.strip()
        if any(c.isupper() for c in raw) and "_" not in raw:
            s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", raw)
            s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
            return _compact_operation_id_snake(s2.lower().replace("-", "_"))
        return _compact_operation_id_snake(raw.lower().replace("-", "_"))
    slug = f"{method.lower()}_{path}"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug).strip("_").lower()
    return slug or "operation"


def _doc_lines(operation: Mapping[str, Any]) -> list[str]:
    """Normalize ``summary`` / ``description`` into wrapped doc lines."""

    text = operation.get("description") or operation.get("summary") or ""
    if not isinstance(text, str) or not text.strip():
        return [operation.get("operationId", "Generated endpoint")]
    lines: list[str] = []
    for i, block in enumerate(text.split("\n")):
        if i > 0:
            lines.append("")
        lines.extend(wrap(block.strip(), width=70))
    return lines


def _deref_schema(schema: Any, root: Mapping[str, Any]) -> Any:
    """Resolve leading ``$ref`` chains against ``components.schemas``."""

    seen: set[str] = set()
    cur = schema
    while isinstance(cur, dict) and "$ref" in cur:
        ref = cur["$ref"]
        if not isinstance(ref, str) or ref in seen:
            return cur
        seen.add(ref)
        m = _REF_SCHEMA.match(ref)
        if not m:
            return cur
        name = m.group(1)
        schemas = root.get("components", {}).get("schemas", {})
        nxt = schemas.get(name)
        if nxt is None:
            return cur
        cur = nxt
    return cur


def _ref_leaf_name(schema: Mapping[str, Any]) -> str | None:
    """Return ``Foo`` from ``{\"$ref\": \"#/components/schemas/Foo\"}``."""

    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return None
    m = _REF_SCHEMA.match(ref)
    if not m:
        return None
    return m.group(1)


def _param_ts(schema: Any, root: Mapping[str, Any]) -> str:
    """Map a parameter JSON Schema to a TypeScript type string."""

    if schema is None:
        return "unknown"
    return json_schema_to_ts(schema, root)


def _extract_json_body_schema(
    operation: Mapping[str, Any],
) -> Any | None:
    """Return the ``application/json`` request body schema if any."""

    rb = operation.get("requestBody")
    if not isinstance(rb, dict):
        return None
    content = rb.get("content")
    if not isinstance(content, dict):
        return None
    for mime in ("application/json", "application/json; charset=utf-8"):
        block = content.get(mime)
        if isinstance(block, dict) and "schema" in block:
            return block["schema"]
    return None


def _pick_response_schema(
    operation: Mapping[str, Any],
) -> Any | None:
    """Pick the first JSON success response schema."""

    responses = operation.get("responses")
    if not isinstance(responses, dict):
        return None
    for code in ("200", "201", "204"):
        block = responses.get(code)
        if not isinstance(block, dict):
            continue
        content = block.get("content")
        if not isinstance(content, dict):
            continue
        for mime in ("application/json", "application/json; charset=utf-8"):
            inner = content.get(mime)
            if isinstance(inner, dict) and "schema" in inner:
                return inner["schema"]
    return None


def _response_ts(schema: Any, root: Mapping[str, Any]) -> str:
    """Choose a TypeScript type for a response schema."""

    if schema is None:
        return "unknown"
    if isinstance(schema, dict):
        leaf = _ref_leaf_name(schema)
        if leaf and "[" not in leaf:
            return leaf
    text = json_schema_to_ts(schema, root)
    if text and text != "unknown":
        return text
    return "unknown"


def _body_model_from_schema(
    schema: Any,
    root: Mapping[str, Any],
) -> tuple[GenBodyModel | None, list[tuple[str, str]], str | None]:
    """Split body into named model + inline property typings."""

    if schema is None:
        return None, [], None
    top_leaf: str | None = None
    if isinstance(schema, dict):
        top_leaf = _ref_leaf_name(schema)
    deref = _deref_schema(schema, root)
    if isinstance(deref, dict) and isinstance(deref.get("properties"), dict):
        props = deref["properties"]
        assert isinstance(props, dict)
        fields = [GenField(name=k) for k in props]
        inline: list[tuple[str, str]] = []
        for k, sub in props.items():
            inline.append((k, json_schema_to_ts(sub, root)))
        if top_leaf:
            return GenBodyModel(name=top_leaf, fields=fields), [], top_leaf
        return None, inline, None
    if top_leaf:
        return GenBodyModel(name=top_leaf, fields=[]), [], top_leaf
    return None, [], None


def _compute_is_mutation(method: str, op_snake: str) -> bool:
    """Mirror ``ResiRoute.is_mutation`` heuristics from ``resi_web``."""

    m = method.upper()
    if m == "GET":
        return False
    if m == "POST" and "list" in op_snake.lower():
        return False
    return True


def _build_arg_type_ts(
    route: GenRoute,
    uses_list_query_contract: bool,
) -> str:
    """Compose the RTK ``Arg`` generic (second type parameter)."""

    def render_inline(args: list[tuple[str, str]]) -> str:
        """Format inline object types for TypeScript."""

        lines = [f"                {n}: {t}," for n, t in args]
        return "{\n" + "\n".join(lines) + "\n            }"

    uses_lqr = uses_list_query_contract and (
        route.body_schema_name == "ListQueryRequest"
    )

    if not route.path_args and not route.query_args:
        if route.body_m:
            return "ListQueryRequest" if uses_lqr else route.body_m.name
        if route.body_args:
            if uses_lqr:
                return "ListQueryRequest"
            return render_inline(route.body_args)
        if route.body_schema_name:
            return route.body_schema_name
        return "{}"

    parts: list[str] = []
    if route.body_m:
        parts.append("ListQueryRequest" if uses_lqr else route.body_m.name)
    elif route.body_args:
        if uses_lqr:
            parts.append("ListQueryRequest")
        else:
            parts.append(render_inline(route.body_args))

    inline = []
    for n, t in route.path_args:
        inline.append(f"                {n}: {t},")
    for n, t in route.query_args:
        inline.append(f"                {n}: {t},")
    parts.append("{\n" + "\n".join(inline) + "\n            }")
    return " & ".join(parts)


def routes_by_primary_tag(spec: Mapping[str, Any]) -> dict[str, list[GenRoute]]:
    """Group OpenAPI operations by their first tag.

    Args:
        spec: Parsed OpenAPI 3.x document.

    Returns:
        Mapping of primary tag string to ordered :class:`GenRoute` lists.
    """

    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return {}
    by_tag: dict[str, list[GenRoute]] = {}
    for path, path_item in paths.items():
        if not isinstance(path, str) or not isinstance(path_item, dict):
            continue
        if any(path.startswith(p) for p in _SKIP_PATH_PREFIXES):
            continue
        for method_l, operation in path_item.items():
            if method_l.lower() not in _HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            tags = operation.get("tags")
            if not isinstance(tags, list) or not tags:
                continue
            tag0 = tags[0]
            if not isinstance(tag0, str) or not tag0.strip():
                continue
            primary = tag0.strip()
            method = method_l.upper()
            op_snake = _operation_snake(operation, method, path)
            name_camel = _snake_to_camel(op_snake)
            name_pascal = _snake_to_pascal(op_snake)

            path_args: list[tuple[str, str]] = []
            query_args: list[tuple[str, str]] = []
            params = operation.get("parameters")
            if isinstance(params, list):
                for p in params:
                    if not isinstance(p, dict):
                        continue
                    pin = p.get("in")
                    pname = p.get("name")
                    path_or_query = pin in ("path", "query")
                    if not path_or_query or not isinstance(pname, str):
                        continue
                    schema = p.get("schema")
                    ts = _param_ts(schema, spec)
                    if pin == "path":
                        path_args.append((pname, ts))
                    else:
                        query_args.append((pname, ts))

            body_schema = _extract_json_body_schema(operation)
            body_m, body_args, body_leaf = _body_model_from_schema(
                body_schema,
                spec,
            )
            body_schema_name = body_leaf

            resp_schema = _pick_response_schema(operation)
            response_ts = _response_ts(resp_schema, spec)

            gr = GenRoute(
                name=op_snake,
                name_snake_case=op_snake,
                name_camel=name_camel,
                name_pascal=name_pascal,
                method=GenMethod(name=method),
                path=path,
                doc_lines=_doc_lines(operation),
                path_args=path_args,
                query_args=query_args,
                body_m=body_m,
                body_args=body_args,
                body_schema_name=body_schema_name,
                response_ts=response_ts,
                is_mutation=_compute_is_mutation(method, op_snake),
            )
            by_tag.setdefault(primary, []).append(gr)

    for routes in by_tag.values():
        for r in routes:
            uses = any(x.body_schema_name == "ListQueryRequest" for x in routes)
            r.arg_type_ts = _build_arg_type_ts(r, uses_list_query_contract=uses)
    return by_tag


def tag_file_stem(tag: str) -> str:
    """File basename (snake) for a primary OpenAPI tag."""

    return re.sub(r"(?<!^)(?=[A-Z])", "_", tag).lower()
