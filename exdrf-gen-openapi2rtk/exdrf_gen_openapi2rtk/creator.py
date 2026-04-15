"""Emit RTK Query TypeScript from a parsed OpenAPI document."""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

import click
from attrs import define, field
from exdrf_gen.fs_support import Base, Dir, File

from exdrf_gen_openapi2rtk.endpoint_keys import assert_unique_rtk_endpoint_keys
from exdrf_gen_openapi2rtk.openapi_cache import (
    fetch_openapi_url_cached,
    load_openapi_from_file,
)
from exdrf_gen_openapi2rtk.spec_routes import (
    GenRoute,
    routes_by_primary_tag,
    tag_file_stem,
)

if TYPE_CHECKING:
    from jinja2 import Environment

logger = logging.getLogger(__name__)

_IN_STATE = {"tenant": "Tenant"}


def _restrict_templates_to_package(env: "Environment", suffix: str) -> None:
    """Limit Jinja search paths to this package's template directory."""

    loader = getattr(env, "loader", None)
    if loader is None:
        return
    paths = list(getattr(loader, "paths", []))
    filtered = [p for p in paths if str(p).endswith(suffix)]
    setattr(loader, "paths", filtered)


def _category_camel(tag: str) -> str:
    """Derive ``c_camel`` from a primary OpenAPI tag string."""

    if not tag:
        return tag
    return tag[0].lower() + tag[1:]


def _used_schema_names(routes: list[GenRoute]) -> list[str]:
    """Collect named schema tokens imported from ``types_import``."""

    names: set[str] = set()
    for r in routes:
        if r.body_m:
            names.add(r.body_m.name)
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", r.response_ts):
            names.add(r.response_ts)
    return sorted(names)


def _build_api_bundle(
    category: str,
    routes: list[GenRoute],
    *,
    types_import: str,
    m_name: str,
) -> dict[str, Any]:
    """Assemble the Jinja context for one per-tag ``*.ts`` module."""

    assert_unique_rtk_endpoint_keys(category, routes)

    c_snake = tag_file_stem(category)
    c_camel = _category_camel(category)
    uses_list_query_contract = any(
        r.body_schema_name == "ListQueryRequest" for r in routes
    )
    used_res_names = _used_schema_names(routes)

    global_sourced = {
        **{
            arg: f"(api.getState() as LocalState).runtime.{arg}.id"
            for arg in _IN_STATE
        },
    }

    def has_local_state(rs: list[GenRoute]) -> bool:
        """True when any route body references ``_IN_STATE`` keys."""

        for r in rs:
            if r.body_m:
                for fld in r.body_m.fields:
                    if fld.name in _IN_STATE:
                        return True
        return False

    def get_local_state(fld: Any) -> str:
        """Map a body field to its global-state TypeScript type label."""

        return _IN_STATE[fld.name]

    def get_arg(arg: str) -> str:
        """Build the JavaScript expression for one request argument."""

        if arg in global_sourced:
            return global_sourced[arg]
        return "args." + arg

    arg_pattern = re.compile(r"\{([^}]+)\}")

    def get_route(route: GenRoute) -> str:
        """Interpolate path and query template literals for RTK ``url``."""

        result = arg_pattern.sub(
            lambda m: "${" + get_arg(m.group(1)) + "}",
            route.path,
        )
        if route.query_args:
            result += "?" + "&".join(
                q[0] + "=${" + get_arg(q[0]) + "}" for q in route.query_args
            )
        return result

    def get_arg_type(route: GenRoute) -> str:
        """Return the precomputed RTK args type for ``route``."""

        return route.arg_type_ts

    def get_response_type(route: GenRoute) -> str:
        """Return the precomputed RTK response type for ``route``."""

        return route.response_ts

    def get_body_arg_names(route: GenRoute) -> list[str]:
        """Return JSON body property names for ``route``."""

        if route.body_m:
            return [f.name for f in route.body_m.fields]
        return [n for n, _ in route.body_args]

    kind_str = ["mutation" if r.is_mutation else "query" for r in routes]

    return {
        "tag_snake": c_snake,
        "category": category,
        "routes": routes,
        "c_snake": c_snake,
        "c_camel": c_camel,
        "r_count": len(routes),
        "r_snake": [r.name_snake_case for r in routes],
        "r_camel": [r.name_camel for r in routes],
        "r_pascal": [r.name_pascal for r in routes],
        "uses_list_query_contract": uses_list_query_contract,
        "used_res_names": used_res_names,
        "used_res": {n: None for n in used_res_names},
        "kind_str": kind_str,
        "global_sourced": global_sourced,
        "get_arg": get_arg,
        "get_route": get_route,
        "get_arg_type": get_arg_type,
        "get_response_type": get_response_type,
        "get_local_state": get_local_state,
        "has_local_state": has_local_state,
        "get_body_arg_names": get_body_arg_names,
        "in_state": _IN_STATE,
        "types_import": types_import,
        "m_name": m_name,
    }


@define
class _RoutesPackageDir(Base):
    """Emit ``index.ts`` plus one ``{tag_snake}.ts`` file per OpenAPI tag."""

    name: str = field()
    bundles: list[dict[str, Any]] = field(factory=list)
    extra: dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs: Any) -> None:
        """Create the routes directory and all per-tag RTK modules."""

        mapping = {**self.extra, **kwargs}
        c_path = self.create_directory(out_path, self.name, **mapping)
        env = mapping["env"]
        child_kw = {k: v for k, v in mapping.items() if k != "env"}
        File("index.ts", "openapi2rtk/index.ts.j2").generate(
            c_path,
            env=env,
            **child_kw,
        )
        for b in self.bundles:
            File("{tag_snake}.ts", "openapi2rtk/api.ts.j2").generate(
                c_path,
                env=env,
                **{**child_kw, **b},
            )


def generate_openapi2rtk(
    spec: Mapping[str, Any],
    routes_out_dir: str,
    env: "Environment",
    *,
    types_import: str,
    base_api_profile: str,
    m_name: str,
) -> None:
    """Write RTK route modules and shared helpers next to ``routes_out_dir``."""

    by_category = routes_by_primary_tag(spec)
    if not by_category:
        logger.warning(
            "OpenAPI document produced no tagged operations; no TS files.",
        )

    bundles: list[dict[str, Any]] = []
    for cat in sorted(by_category):
        routes = by_category[cat]
        if not routes:
            continue
        bundles.append(
            _build_api_bundle(
                cat,
                routes,
                types_import=types_import,
                m_name=m_name,
            )
        )

    c_keys = sorted(by_category.keys())
    c_camel = [_category_camel(c) for c in c_keys]
    c_snake = [tag_file_stem(c) for c in c_keys]
    glb_vars: dict[str, Any] = {
        "c_count": len(c_keys),
        "c_keys": c_keys,
        "c_snake": c_snake,
        "c_camel": c_camel,
        "categories": by_category,
        "m_name": m_name,
    }

    routes_path = Path(routes_out_dir)
    parent = str(routes_path.parent)
    routes_folder_name = routes_path.name

    base_tpl = (
        "openapi2rtk/base-api.fr_one.ts.j2"
        if base_api_profile == "fr_one"
        else "openapi2rtk/base-api.minimal.ts.j2"
    )

    root = Dir(
        name="",
        comp=[
            File(
                "list-query-contract.ts",
                "openapi2rtk/list-query-contract.ts.j2",
            ),
            File("base-api.ts", base_tpl),
            File("cacheUtils.ts", "openapi2rtk/cacheUtils.ts.j2"),
            _RoutesPackageDir(
                name=routes_folder_name,
                bundles=bundles,
            ),
        ],
    )
    root.generate(
        parent,
        env=env,
        **glb_vars,
    )


def run_openapi2rtk(
    context: click.Context,
    routes_out_dir: str,
    openapi_file: str | None,
    openapi_url: str | None,
    cache_file: str | None,
    types_import: str,
    base_api_profile: str,
) -> None:
    """CLI entry: load spec, then emit RTK TypeScript."""

    env = context.obj["jinja_env"]
    _restrict_templates_to_package(env, "openapi2rtk_templates")

    if openapi_file:
        spec = load_openapi_from_file(openapi_file)
    elif openapi_url:
        if not cache_file:
            click.echo(
                "--cache-file is required when using --openapi-url.",
                err=True,
            )
            sys.exit(1)
        spec = fetch_openapi_url_cached(openapi_url, Path(cache_file))
    else:
        click.echo(
            "Provide --openapi-file or --openapi-url (with --cache-file).",
            err=True,
        )
        sys.exit(1)

    generate_openapi2rtk(
        spec,
        routes_out_dir,
        env,
        types_import=types_import,
        base_api_profile=base_api_profile,
        m_name="exdrf_gen_openapi2rtk.creator",
    )
