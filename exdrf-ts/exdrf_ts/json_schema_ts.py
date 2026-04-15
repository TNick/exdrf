"""Map OpenAPI / JSON Schema fragments to TypeScript type strings."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

_REF_RE = re.compile(r"^#/components/schemas/([A-Za-z0-9_.-]+)$")


def _json_pointer_get(doc: Mapping[str, Any], pointer: str) -> Any:
    """Resolve a JSON Pointer (RFC 6901) against ``doc``.

    Only supports absolute pointers starting with ``/`` (no URI fragment).

    Args:
        doc: JSON object to traverse.
        pointer: Pointer such as ``/components/schemas/Foo``.

    Returns:
        The value at ``pointer``, or ``None`` if a segment is missing.
    """

    if not pointer.startswith("/"):
        return None
    cur: Any = doc
    for raw in pointer.strip("/").split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(cur, Mapping) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _resolve_ref(
    ref: str,
    resolve_root: Mapping[str, Any],
    seen_refs: frozenset[str],
) -> tuple[Any, frozenset[str]] | None:
    """Follow an OpenAPI ``#/components/schemas/...`` reference.

    Args:
        ref: Reference string from ``"$ref"``.
        resolve_root: Full OpenAPI document (or object containing
            ``components``).
        seen_refs: References already followed (cycle guard).

    Returns:
        ``(target_schema, seen_refs_with_ref)`` or ``None`` if unsupported.
    """

    m = _REF_RE.match(ref)
    if not m:
        return None
    name = m.group(1)
    if ref in seen_refs:
        return None
    pointer = f"/components/schemas/{name}"
    target = _json_pointer_get(resolve_root, pointer)
    if target is None:
        return None
    return target, frozenset((*seen_refs, ref))


def json_schema_to_ts(
    schema: Any,
    resolve_root: Mapping[str, Any] | None = None,
    *,
    seen_refs: frozenset[str] | None = None,
) -> str:
    """Convert a JSON Schema fragment to a TypeScript type string.

    Intended for OpenAPI 3.x ``components.schemas`` and inline parameter /
    response bodies. Unsupported or cyclic constructs fall back to
    ``unknown``.

    Args:
        schema: Schema object (``dict``), ``True`` (accept-all schema in JSON
            Schema drafts), or ``False`` (reject-all; emitted as ``never``).
        resolve_root: Document used to resolve ``#/components/schemas/...``
            ``"$ref"`` values. When ``None``, ``"$ref"`` resolves to
            ``unknown``.
        seen_refs: Internal recursion guard; do not pass from callers.

    Returns:
        TypeScript type text.
    """

    stack = frozenset() if seen_refs is None else seen_refs

    if schema is True:
        return "unknown"
    if schema is False:
        return "never"
    if not isinstance(schema, Mapping):
        return "unknown"

    ref = schema.get("$ref")
    if isinstance(ref, str) and resolve_root is not None:
        resolved = _resolve_ref(ref, resolve_root, stack)
        if resolved is not None:
            sub, new_stack = resolved
            return json_schema_to_ts(sub, resolve_root, seen_refs=new_stack)
        m = _REF_RE.match(ref)
        if m:
            return m.group(1)
        return "unknown"

    if "enum" in schema and isinstance(schema["enum"], list):
        literals: list[str] = []
        for v in schema["enum"]:
            if isinstance(v, str):
                literals.append(json.dumps(v))
            elif isinstance(v, bool):
                literals.append("true" if v else "false")
            elif v is None:
                literals.append("null")
            elif isinstance(v, (int, float)):
                literals.append(json.dumps(v))
        if not literals:
            return "unknown"
        return " | ".join(literals)

    if "oneOf" in schema and isinstance(schema["oneOf"], list):
        parts = [
            json_schema_to_ts(s, resolve_root, seen_refs=stack)
            for s in schema["oneOf"]
        ]
        parts_u = [p for p in parts if p != "unknown"]
        if not parts_u:
            return "unknown"
        return " | ".join(dict.fromkeys(parts_u))

    if "anyOf" in schema and isinstance(schema["anyOf"], list):
        parts = [
            json_schema_to_ts(s, resolve_root, seen_refs=stack)
            for s in schema["anyOf"]
        ]
        parts_u = [p for p in parts if p != "unknown"]
        if not parts_u:
            return "unknown"
        return " | ".join(dict.fromkeys(parts_u))

    if "allOf" in schema and isinstance(schema["allOf"], list):
        parts = [
            json_schema_to_ts(s, resolve_root, seen_refs=stack)
            for s in schema["allOf"]
        ]
        if all(p == "unknown" for p in parts):
            return "unknown"

        def _part(p: str) -> str:
            if " | " in p or " & " in p:
                return f"({p})"
            return p

        return " & ".join(_part(p) for p in parts)

    type_val = schema.get("type")
    types: list[str] = []
    if isinstance(type_val, list):
        types = [t for t in type_val if isinstance(t, str)]
    elif isinstance(type_val, str):
        types = [type_val]

    nullable = schema.get("nullable") is True

    def _wrap_null(t: str) -> str:
        if nullable:
            return f"{t} | null"
        return t

    if not types:
        if "properties" in schema or "additionalProperties" in schema:
            return _wrap_null(_object_to_ts(schema, resolve_root, stack))
        return "unknown"

    out_parts: list[str] = []
    for t in types:
        if t == "string":
            out_parts.append("string")
        elif t == "integer":
            out_parts.append("number")
        elif t == "number":
            out_parts.append("number")
        elif t == "boolean":
            out_parts.append("boolean")
        elif t == "null":
            out_parts.append("null")
        elif t == "array":
            items = schema.get("items", {})
            inner = json_schema_to_ts(items, resolve_root, seen_refs=stack)
            out_parts.append(f"{inner}[]")
        elif t == "object":
            out_parts.append(_object_to_ts(schema, resolve_root, stack))
        else:
            out_parts.append("unknown")

    merged = " | ".join(dict.fromkeys(out_parts)) if out_parts else "unknown"
    return _wrap_null(merged)


def _object_to_ts(
    schema: Mapping[str, Any],
    resolve_root: Mapping[str, Any] | None,
    stack: frozenset[str],
) -> str:
    """Build an inline object type from schema ``properties`` / ``additional``.

    Args:
        schema: JSON Schema with ``type`` ``object`` (or implied).
        resolve_root: Document for ``$ref`` inside nested schemas.
        stack: Active ``$ref`` stack.

    Returns:
        Inline TypeScript object type or ``Record<...>``.
    """

    props = schema.get("properties")
    required = set(schema.get("required", []) or [])
    if isinstance(props, Mapping) and props:
        lines: list[str] = []
        for key, sub in props.items():
            opt = "" if key in required else "?"
            ts = json_schema_to_ts(sub, resolve_root, seen_refs=stack)
            safe_key = (
                key
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(key))
                else json.dumps(str(key))
            )
            lines.append(f"  {safe_key}{opt}: {ts};")
        return "{\n" + "\n".join(lines) + "\n}"

    addl = schema.get("additionalProperties")
    if addl is True:
        return "{ [key: string]: unknown }"
    if isinstance(addl, Mapping):
        inner = json_schema_to_ts(addl, resolve_root, seen_refs=stack)
        return f"{{ [key: string]: {inner} }}"
    return "{ [key: string]: unknown }"
