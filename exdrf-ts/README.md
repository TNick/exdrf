# exdrf-ts

**exdrf-ts** maps **exdrf** field-type constants and Python typing objects to
**TypeScript** strings and DARE field class names. Code generators
(**exdrf-gen-pd2dare**, **exdrf-gen-openapi2rtk**, app-specific pipelines)
import it when emitting TS from Pydantic-backed or OpenAPI-backed resources.

The PyPI distribution name is **`exdrf-ts`**. The import package is
**`exdrf_ts`**.

Python **3.12.2+** is required. Runtime dependencies: **exdrf** and
**exdrf-pd**.

## Installation

```text
pip install exdrf-ts
```

Editable install from the exdrf monorepo root (with other packages present as
needed):

```text
pip install -e ./exdrf-ts
```

## API

- **`py_type_to_ts`**: Python annotation or runtime type to TS type string.
- **`type_to_field_class`**: Maps **exdrf** `FIELD_TYPE_*` values to DARE
  field class names (for example `StringField`).
- **`model_rel_import`**: Relative import path between two models (via
  **`exdrf_pd.visitor.ExModelVisitor`**).

## Role in the stack

- **`exdrf`**: core dataset / field model.
- **`exdrf-pd`**: Pydantic **`ExModel`** and visitors.
- **`exdrf-ts`**: TypeScript-oriented views of those types.
