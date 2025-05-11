# SqlAlchemy Support for Ex-DRF

The library provides guidance and support code for using SQLAlchemy with Ex-DRF.

## Usage

Start by basing your models off `Base` from `exdrf_al.base` module.
It is a rather simple class that allows for model andd fields
iteration. If you don't want to use it, take a look at the
implementation of that class for how to extract the information
you need from your models.

### Models

The library reads the description of models from the sqlAlchemy metadata. On top of that you cad add additional information by adding
members to the `info` key in the `__table_args__` model attribute.

The keys that are used inside the `info` dictionary are documented
in `exdrf.resource.ResExtraInfo`, which is the pydantic class that
parses the information. Here is brief description of the most
important keys:

- `label`: takes a string that is interpreted by the DSL in `exdrf.
  label_dsl`; it is used to generate code that computes the label of
  a record given the record. The `exdrf.label_dsl` module includes
  code to create python and typescript code from a parsed
  label definition.

Example:

```python
class Example(Base):
    __tablename__ = "the_table"
    __table_args__ = {
        "info": {
            "label": """(if name name (concat "ID:" " id))""",
        }
    }
    id: int
    name: Optional[str] = None
```

### Fields

Just like with the models, the model field metadata is used to
extract the information. Additionally, we use values in the dictionary assigned to the `info` attribute to add additional information.

The keys that are used inside the `info` consist of a common subset
for all field types and specific keys for each field type. The common keys parsed by the `exdrf.field.FieldInfo` class are documented with
that class, and each field type is described in its own module under
`exdrf.field_types`.

Example:

```python
class Example(Base):
    __tablename__ = "the_table"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="The unique identifier for a record within its table",
        info={
            "sortable": False
        }
    )
    name: Mapped[Optional[str]] = mapped_column(
        doc="The name of the record",
        info={
            "filterable": False,
            "multiline": True,
            "min_length": 3,
        }
    )
```
