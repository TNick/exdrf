# exdrf-gen-pd2dare

**exdrf-gen-pd2dare** is an **`exdrf-gen`** plugin that emits **DARE**
TypeScript resources (`*.ts`), a per-category **`index.ts`**, and a root
**`dataset.ts`** from **Pydantic `ExModel`** subclasses (names ending in `Ex`).

The PyPI distribution name is **`exdrf-gen-pd2dare`**; the import package is
**`exdrf_gen_pd2dare`**.

## Installation

Install **`exdrf-gen`** plus this plugin (and their stacks):

```text
pip install exdrf-gen-pd2dare
```

Editable monorepo install:

```text
pip install -e ./exdrf-gen-pd2dare
```

## Command-line interface

After installation, **`exdrf-gen --help`** lists **`pd2dare`**.

```text
exdrf-gen pd2dare /path/to/out
```

Or:

```text
python -m exdrf_gen pd2dare /path/to/out
```

The output directory must exist (create it in your Makefile or shell script).

### Environment variables

- **`EXDRF_PYDANTIC_MODELS_MODULES`**: comma-separated module names to import
  before building the dataset (see **`exdrf_pd.model_import`**). If unset,
  **`RESI_PYDANTIC_MODELS_MODULES`** is used as a deprecated fallback.
- **`EXDRF_PD2DARE_PATH`**: default output directory when the path argument is
  omitted.

## Templates

Jinja templates live under **`exdrf_gen_pd2dare/pd2dare_templates/`** and are
registered via **`install_plugin`**.

## Related packages

- **`exdrf-gen`** — shared CLI and Jinja environment.
- **`exdrf-pd`** — Pydantic loaders and **`dataset_from_pydantic`**.
- **`exdrf-ts`** — field / Python type to TypeScript mapping.
