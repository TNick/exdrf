# Pydantic support for Ex-DRF

**exdrf-pd** connects **Pydantic v2** models to the **exdrf** dataset tree. It
is the usual path for HTTP APIs and validators that prefer **`BaseModel`** over
SQLAlchemy declarative classes.

## What it provides

- **`ExModel`** subclasses and visitors that expose resources and fields in the
  same shapes **exdrf** uses elsewhere, so codegen and tooling can treat ORM and
  Pydantic sources uniformly where supported.
- **`dataset_from_pydantic`** (and related imports under **`exdrf_pd`**) for
  building an **`ExDataset`** from your model modules—used by plugins such as
  **exdrf-gen-pd2dare**.

## Dependencies

**exdrf** and **pydantic** (see `pyproject.toml`). Python **3.12.2+** is
required.

## Related packages

- **exdrf-gen-al2pd** — emits Pydantic `Xxx` / `XxxEx` / `XxxCreate` / `XxxEdit`
  from SQLAlchemy metadata (often paired with **exdrf-gen-al2r**).
- **exdrf-ts** — maps field types and Python annotations to TypeScript for DARE
  and other TS emitters; depends on **exdrf-pd**.
- **exdrf-gen-pd2dare** — generates DARE TypeScript from **`ExModel`** classes.

Install **exdrf-gen** and the plugin you need; see **`exdrf-gen`** README for
the plugin entry-point pattern.
