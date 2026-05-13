# exdrf-gen-openapi2rtk

**exdrf-gen-openapi2rtk** is an **`exdrf-gen`** plugin that turns an **OpenAPI
3.x** JSON document into **RTK Query** TypeScript modules (endpoints, hooks, and
generated request/response wiring). It can load a local file or fetch a remote
spec with optional HTTP caching.

Python **3.12.2+** is required. Dependencies (**`attrs`**, **`click`**,
**`exdrf-gen`**, **`exdrf-ts`**) are listed in `pyproject.toml`.

## Plugin registration

```toml
[project.entry-points.'exdrf.plugins']
exdrf_gen = 'exdrf_gen_openapi2rtk'
```

Install **`exdrf-gen`** and **`exdrf-gen-openapi2rtk`** in the same environment;
then **`exdrf-gen --help`** lists **`openapi2rtk`**.

## Usage

### CLI

The command is registered on the shared **`exdrf-gen`** CLI as
**`openapi2rtk`**:

```bash
python -m exdrf_gen openapi2rtk /path/to/routes/out \
  --openapi-file /path/to/openapi.json \
  --types-import "@app/models" \
  --base-api-profile minimal
```

Use **`--base-api-profile fr_one`** when generating for the **fr-one** customer
SPA (same wiring as historical **`resi_gen r2ts`** output).

Remote specs: pass **`--openapi-url`** (and optional cache flags) instead of or
in addition to **`--openapi-file`**—see **`exdrf-gen --help`** / subcommand help
for the exact options in your installed version.

## See also

- **`resi_gen r2ts`** in **bk-one** snapshots **`app.openapi()`**, then calls
  this generator with **`--types-import @resi/models`** and **`fr_one`** base
  API.
- **`exdrf-gen`** — shared CLI, Jinja environment, and plugin loading.
- **`exdrf-ts`** — type mapping helpers used during emission.
