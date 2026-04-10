# exdrf-gen

`exdrf-gen` is a Python library for **generating text and project structure from
Jinja2 templates**, built around the **`exdrf`** dataset model (resources,
fields, categories). It supplies a shared Jinja environment tuned for that
domain, optional **composite file-tree builders** that iterate over an
`ExDataset`, a small **Click-based CLI scaffold**, and a **plugin hook** so other
packages can extend templates and Jinja globals.

The PyPI distribution name is **`exdrf-gen`**; the import package is
**`exdrf_gen`**. Python **3.12.10+** is required.

## Role in the exdrf stack

- **`exdrf`** describes datasets, resources, and fields.
- **`exdrf-gen`** renders those descriptions (and arbitrary template context)
  through Jinja2, and can emit nested directories/files in one pass.
- Sibling packages such as **`exdrf-gen-al2pd`**, **`exdrf-gen-al2qt`**, etc.
  register as `exdrf.plugins` entry points named `exdrf_gen` and build on this
  layer for specific targets (e.g. pandas, Qt).

## Installation

Install the core package (pulls `exdrf`, Click, Jinja2, dotenv loaders, and
`inflect` per `pyproject.toml`):

```text
pip install exdrf-gen
```

If you use **`exdrf_gen.fs_support`** (composite generators), you also need
**`exdrf-al`**: that module imports `exdrf_al.calc_q` for related-model helpers.
Install it in the same environment when you rely on `ResFile`, `TopDir`, and
similar APIs.

## Command-line interface

Installing **`exdrf-gen`** adds the **`exdrf-gen`** console script
(`[project.scripts]` → **`exdrf_gen.__main__:main`**). It calls
**`plugin_support.load_plugins()`** (so sibling **`exdrf.plugins`** / **`exdrf_gen`**
packages register templates and commands), then runs the root Click group.

```text
exdrf-gen --help
exdrf-gen --debug <subcommand> ...
```

Equivalent when the package is on **`PYTHONPATH`**:

```text
python -m exdrf_gen --help
```

Subcommands (e.g. **`al2at`**, **`al2qt`**) come from plugins; install the
matching **`exdrf-gen-*`** distribution to enable them.

## Package layout (`exdrf_gen`)

### `jinja_support`

Central Jinja2 integration.

- **`Loader`**: custom `jinja2.BaseLoader` that resolves a template name in
  order: absolute file path; path under each configured search directory (with
  `/` as the path separator); or a **Python module path** of the form
  `package.subpkg/template_name`, which loads `template_name` or
  `template_name.j2` next to the imported package’s `__file__`.
- **`create_jinja_env(auto_reload=False)`**: builds an `Environment` with that
  loader, auto-escaping, and a large set of **globals**, **filters**, and one
  custom **test** (`None`).
- **Module singleton `jinja_env`**: default environment from
  `create_jinja_env()`.
- **`recreate_global_env()`**: replaces the global `jinja_env` with a fresh
  environment (e.g. `auto_reload=True` for development).

The environment is oriented toward **documentation and UI-ish output**: string
and number formatting, dates, `inflect`-backed pluralization, snake_case helpers,
`to_json` with optional attribute exclusion, list utilities (`sorted` variants,
`equals` / `not_equals` / `contains` filters), rounding modes, and symbolic
**navigation URLs** (`exdrf://navigation/resource/...`) plus CSS class names for
internal links and deleted records.

### `fs_support`

**Composite generators** for walking an **`ExDataset`** and emitting files or
directories. Types are **`attrs`**-based (`@define`).

- **`Base`**: shared **`create_file`**, **`create_directory`**, and
  **`read_preserved`**. Rendering merges template context with **preserved
  regions** read from an existing output file: markers
  `exdrf-keep-start <name>` … `exdrf-keep-end` define blocks that are kept across
  regenerations and exposed to the template (by guard name).
- **`File` / `Dir`**: single file or directory; `Dir` recurses into child
  components.
- **`FieldFile` / `FieldDir`**: one output per field; context includes
  `field_to_args` (names, docs, types, ref flags, etc.).
- **`ResFile` / `ResDir`**: one output per resource (model); context includes
  `resource_to_args` (pascal/snake names, docs, primary fields, related-model
  lists from `exdrf_al`, etc.).
- **`CategFile` / `CategDir`**: one output per **category** from the dataset.
- **`TopDir`**: root of a tree; injects `resources`, `categ_map`,
  `zero_categories()`, and `sorted_by_deps()` into children.

Use these when your generator maps **dataset topology** to **folder layout**
(e.g. one folder per model, one file per field).

### `cli_base`

Minimal **Click** application (driven by **`exdrf_gen.__main__.main`** and the
**`exdrf-gen`** script):

- **`cli`**: root group with `--debug/--no-debug`, loads `.env` via
  **`python-dotenv`**, and stores **`create_context_obj(debug)`** on
  `ctx.obj`.
- **`create_context_obj`**: configures logging and returns a dict with
  **`jinja_env`** and **`inflect`** (`exdrf.utils.inflect_e`) for subcommands.

Downstream packages typically add subcommands to this group or reuse
`create_context_obj`.

### `plugin_support`

- **`load_plugins()`**: discovers **`importlib.metadata` entry points** in group
  **`exdrf.plugins`** and loads each plugin whose **name** is **`exdrf_gen`**
  (sibling generator packages use this to register side effects on import).
- **`install_plugin(...)`**: extends the shared **`jinja_env`**—extra template
  search paths on the loader, and optional **tests**, **globals**, and
  **filters** (with warnings when names collide).

### `py_support`

**`ModuleSymbol`**: a **`click.ParamType`** that resolves a string like
`package.module:symbol` via **`exdrf.py_support.get_symbol_from_path`** for CLI
arguments that refer to callables or objects.

### `utils`

Reserved for small shared helpers; currently empty.

### Version

**`exdrf_gen.__version__`** is generated by **setuptools-scm** into
`exdrf_gen/__version__.py` at build time (`fallback_version` in
`pyproject.toml`).

## Typical usage patterns

1. **Render a template** with the default environment:

   ```python
   from exdrf_gen.jinja_support import jinja_env

   text = jinja_env.get_template("path/or/module/template.j2").render(...)
   ```

2. **Add template roots or filters** from your package:

   ```python
   from exdrf_gen import plugin_support

   plugin_support.install_plugin(
       template_paths=["/my/templates"],
       extra_globals={"my_helper": my_helper},
   )
   ```

3. **Walk a dataset** with `fs_support.TopDir` and pass **`env=jinja_env`** and
   **`dset=...`** into **`generate(out_path, ...)`**.

## Writing a plugin package

Sibling generators follow the same pattern. Compare these installable packages
in the `exdrf` repo:

- **`exdrf-gen-al2at`** (`exdrf_gen_al2at`) — attrs model output.
- **`exdrf-gen-al2pd`** (`exdrf_gen_al2pd`) — Pydantic-oriented output.
- **`exdrf-gen-al2qt`** (`exdrf_gen_al2qt`) — Qt-related output.

Each one does three things: register an **entry point** so `load_plugins()` can
import it, extend the **shared Jinja environment** on import, and attach
**Click subcommands** to the shared **`cli`** group.

### 1. Declare the `exdrf.plugins` entry point

In `pyproject.toml`, map the fixed entry point **name** `exdrf_gen` to the
**module** that should run when the plugin loads (usually your package’s
top-level `__init__.py`):

```toml
[project.entry-points.'exdrf.plugins']
exdrf_gen = 'exdrf_gen_mytarget'
```

`plugin_support.load_plugins()` loads every distribution that exposes this name
in the `exdrf.plugins` group. Use **one** such entry point per plugin package.

### 2. Register templates (and optional Jinja extensions) at import time

When the entry-point module is imported, call **`install_plugin`** so the
shared **`jinja_env`** can resolve your templates. The **al2\*** packages only
add a template directory; you can also pass **`extra_globals`**,
**`extra_filters`**, or **`extra_tests`**.

Example:

```python
import os

from exdrf_gen.cli_base import cli
from exdrf_gen.plugin_support import install_plugin

install_plugin(
    template_paths=[
        os.path.join(os.path.dirname(__file__), "my_templates"),
    ],
    # optional:
    # extra_globals={"my_helper": my_helper},
)
```

Your package should list **`exdrf-gen`** as a runtime dependency. Flows that
build from SQLAlchemy-backed datasets (like the **al2\*** tools) typically also
need **`exdrf-al`** and **`click`**.

### 3. Add CLI commands to the shared `cli` group

Import **`cli`** from **`exdrf_gen.cli_base`** and register subcommands with
**`@cli.command(...)`**. For rendering, use **`context.obj["jinja_env"]`** (and
other keys from **`create_context_obj`**, such as **`inflect`**).

Sketch matching **al2at** / **al2qt** (pass the environment into your own
generator function):

```python
import click
from exdrf_gen.cli_base import cli


@cli.command(name="mygen")
@click.pass_context
def mygen(context: click.Context, ...):
    env = context.obj["jinja_env"]
    ...
```

The **al2pd** package registers **`al2pd`** the same way but keeps its command
implementation minimal; **al2at** and **al2qt** call into a **`creator`** module
and pass **`env=context.obj["jinja_env"]`** into the generator.

### Loading plugins from an application

The **`exdrf-gen`** script and **`python -m exdrf_gen`** already run
**`load_plugins()`** before **`cli()`**. If you embed the CLI in another app,
do the same (or call **`main`**):

```python
from exdrf_gen.__main__ import main

main()
```

Alternatively, call **`load_plugins()`** then **`cli()`** yourself:

```python
from exdrf_gen import plugin_support
from exdrf_gen.cli_base import cli

plugin_support.load_plugins()
cli()
```

## Development

Optional dev dependencies are listed under **`[project.optional-dependencies]
dev`** in `pyproject.toml` (formatting, linting, tests, build tools). Versioning
uses **setuptools_scm**; see `[tool.setuptools_scm]` in the same file.
