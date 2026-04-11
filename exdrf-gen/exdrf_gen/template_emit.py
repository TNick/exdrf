"""Write Jinja-rendered files for exdrf resources and category trees."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset
    from exdrf.resource import ExResource
    from jinja2 import Template


def write_resource_template_file(
    resource: "ExResource",
    template: "Template",
    path: str,
    extension: str,
    name: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Render ``template`` for one resource and write it under ``path``.

    Mirrors the layout used by application ``Resource.write_file`` helpers:
    category subdirectories, UTF-8 output, sorted dependencies unless
    overridden via ``deps`` / ``dep_paths`` in ``kwargs``.

    Args:
        resource: The exdrf resource (model) to render.
        template: Jinja template instance.
        path: Output root directory.
        extension: File extension without a leading dot.
        name: Optional file base name override.
        **kwargs: Extra template context (may include ``deps`` /
            ``dep_paths`` overrides).
    """

    # Sort dependencies alphabetically unless the caller overrides them.
    render_kw = dict(kwargs)
    deps_override = render_kw.pop("deps", None)
    dep_paths_override = render_kw.pop("dep_paths", None)
    if deps_override is not None:
        deps = deps_override
        if dep_paths_override is not None:
            dep_paths = dep_paths_override
        else:
            dep_paths = [resource.rel_import(dep) for dep in deps]
    else:
        deps = sorted(resource.get_dependencies(), key=lambda x: x.name)
        dep_paths = [resource.rel_import(dep) for dep in deps]

    content = template.render(
        model=resource,
        model_name=resource.name,
        categories=resource.categories,
        doc="\n".join(resource.doc_lines),
        doc_lines=resource.doc_lines,
        fields=resource.fields,
        deps=deps,
        dep_paths=dep_paths,
        **render_kw,
    )

    if not content:
        return

    content = content.rstrip() + "\n"
    file_path = resource.ensure_path(path, extension, name=name)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def write_dataset_category_index(
    dataset: "ExDataset",
    template: "Template",
    path: str,
    file_name: str,
    **kwargs: Any,
) -> None:
    """Emit one index file per category folder from ``dataset.category_map``.

    Args:
        dataset: Dataset whose ``category_map`` drives recursion.
        template: Jinja template for each index file.
        path: Output root directory.
        file_name: Index file name (for example ``index.ts``).
        **kwargs: Extra template context passed to each render.
    """

    def do_map(the_map: dict, parts: list[str]) -> list[Any]:
        """Recursively walk the category tree and write index files."""

        model_list = []
        for map_name in sorted(the_map.keys()):
            value = the_map[map_name]
            if isinstance(value, dict):
                model_list.extend(
                    [(m, map_name) for m in do_map(value, parts + [map_name])]
                )
            else:
                model_list.append((map_name, map_name))

        dir_path = os.path.join(path, *parts)
        file_path = os.path.join(dir_path, file_name)
        content = template.render(
            model_list=model_list,
            crt_path=parts,
            dataset=dataset,
            level=len(parts),
            **kwargs,
        )

        if content:
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        return [m[0] for m in model_list]

    do_map(dataset.category_map, [])
