# Sqlalchemy to Qt

This is a plugin for generating Qt code for Sqlalchemy models using the Exdrf
library.

To use it, make sure that you have the exdrf_gen module in the environment,
then use the following command to generate the code:

```bash
exdrf-gen al2qt
```

## Template Variables Reference

This section documents all the variables available to different template types
used by `generate_qt_from_alchemy`. Templates are organized into four levels:
top-level, category-level, resource-level, and field-level. Each level has
access to its own specific variables plus all variables from parent levels.

### Common Variables Available to All Templates

These variables are available in every template regardless of its level:

- **`source_module`**: The name of the Python module where the generator
  function is defined. This is typically used in generated file headers to
  indicate the source.

- **`source_templ`**: The path to the template file being used to generate the
  output. This helps identify which template was used when reading generated
  files.

- **`dset`**: The dataset object (`ExDataset`) that contains all resources and
  their relationships. You can access any resource using `dset[resource_name]`.

- **`out_module`**: The module name where generated files will be placed. This
  is the value passed to `generate_qt_from_alchemy` as the `out_module`
  parameter.

- **`db_module`**: The module name where the SQLAlchemy database models are
  defined. This is the value passed to `generate_qt_from_alchemy` as the
  `db_module` parameter.

- **`env`**: The Jinja2 template environment used for rendering templates.

### Preserved Content Variables

These variables are automatically preserved when regenerating files. Content
between special comment markers in existing files is preserved and made
available to templates:

- **`other_imports`**: Preserved import statements that should be kept in
  generated files.

- **`other_globals`**: Preserved global variable definitions.

- **`other_attributes`**: Preserved class attributes (varies by template type).

- **`more_content`**: General preserved content at the end of files.

- Template-specific preserved content variables (e.g., `extra_init`,
  `extra_editor_content`, `extra_field_content`, etc.) are documented in
  their respective template sections.

### 1. Top-Level Templates

Top-level templates generate files at the root of the output directory. They
have access to all common variables plus the dataset-level variables below.

#### Template Files

- `menus.py.j2`: Generates menu actions and menus for all resources
- `plugins.py.j2`: Generates plugin hook definitions for all resources
- `router.py.j2`: Generates routing configuration for navigation between
  resources
- `__init__.py.j2`: Generates an empty `__init__.py` file with preserved
  content

#### Available Variables

- **`categ_map`**: A dictionary mapping category names to their resources.
  Each key is a category name (string), and each value is a list of resource
  names belonging to that category.

- **`categ_zero`**: An iterator that yields tuples of (category_name,
  resources_list) for all categories in the dataset. Useful for iterating
  through categories.

- **`resources`**: A list of all resource objects (`ExResource`) in the
  dataset.

- **`resources_sd`**: Resources sorted by their dependencies. Resources that
  depend on others appear after them in this list.

- **`sorted_resources_for_ui(dset, resource_list)`**: A function that sorts
  resources for UI display. By default, it sorts alphabetically, but can be
  customized via the `sr_for_ui` parameter.

### 2. Category-Level Templates

Category-level templates generate files within category directories. They have
access to all common variables, all top-level variables, plus the
category-specific variables below.

#### Category Template Files

- `c/api.py.j2`: Generates the API module that exports all widgets and models
  for resources in this category

- `c/__init__.py.j2`: Generates an `__init__.py` file for the category module

#### Available Variables for Category Template Files

- **`category_snake`**: The category name in snake_case format (lowercase with
  underscores). This is used for directory and module names.

- **`resources`**: A list of all resource objects (`ExResource`) that belong to
  this specific category.

### 3. Resource-Level Templates

Resource-level templates generate files for individual resources (models). They
have access to all common variables, all top-level variables, all
category-level variables, plus the resource-specific variables below.

#### Resource Template Files

- `c/m/api.py.j2`: Generates the API module that exports all widgets and
  models for this specific resource

- `c/m/m_ful.py.j2`: Generates the full model class that contains all fields
  of the resource for table/list displays

- `c/m/m_ocm.py.j2`: Generates the name-only model class that contains only
  the label field, suitable for selectors and comboboxes

- `c/m/single_f.py.j2`: Generates a special label field class that provides a
  human-readable label for the entire record

- `c/m/w/editor.py.j2`: Generates the editor widget class that allows users to
  create and edit records

- `c/m/w/editor.ui.j2`: Generates the Qt UI file (XML) that defines the visual
  layout of the editor widget

- `c/m/w/list.py.j2`: Generates the list widget class that displays a table of
  records

- `c/m/w/selector.py.j2`: Generates single-select and multi-select widget
  classes for choosing records

- `c/m/w/templ_viewer.py.j2`: Generates a template-based viewer widget for
  displaying records using HTML templates

- `c/m/w/view_templ.html.j2`: Generates an HTML template for displaying
  records in the template viewer

- `c/m/__init__.py.j2`: Generates an `__init__.py` file for the resource
  module

#### Available Variables for Resource Template Files

##### Resource Object Variables

- **`r`**: The resource object (`ExResource`) itself. This provides access to
  all properties and methods of the resource.

- **`ResPascal`**: The resource name in PascalCase format (e.g., "UserProfile"
  from "user_profile"). Used for class names.

- **`res_snake`**: The resource name in snake_case format (e.g.,
  "user_profile"). Used for file names and variable names.

- **`res_p_snake`**: The plural form of the resource name in snake_case (e.g.,
  "user_profiles"). Used for directory names.

- **`res_camel`**: The resource name in camelCase format (e.g., "userProfile").
  Used in some variable names.

- **`res_text`**: A human-readable text name for the resource, typically used
  in UI labels.

- **`ResText`**: The capitalized version of `res_text`, used in titles.

- **`res_docs`**: The docstring of the resource split into lines. This
  contains the description of what the resource represents.

- **`categories`**: A list of category names (strings) that this resource
  belongs to. Categories represent nested module paths.

##### Resource Field Information

- **`fields`**: A list of all field objects (`ExField`) belonging to this
  resource, sorted using the resource's field sorting method.

- **`fields_cats`**: A dictionary mapping category names to lists of fields.
  Fields can be organized into categories for better UI organization (tabs in
  editors, sections in forms).

##### Resource Primary Key Information

- **`res_mfs`**: The minimum field set - a list of fields that uniquely
  identify a record when combined. This typically includes the primary key
  fields.

- **`res_spl_id`**: A boolean indicating whether the resource has a simple
  (single-field) primary key. True means one field, False means multiple
  fields form a composite key.

- **`res_primaries`**: A list of field names that form the primary key. For
  simple primary keys, this contains one name; for composite keys, it
  contains multiple names.

##### Resource Relationship Information

- **`all_related_models`**: A list of all resource objects that are related to
  this resource through foreign key relationships. These are resources that can
  be loaded together for efficient database queries.

- **`all_related_paths`**: A list of relationship paths (SQLAlchemy query
  options) that specify how to load related resources. These are used in
  database queries to eagerly load related data.

- **`all_related_label_models`**: Similar to `all_related_models`, but only
  includes resources needed for generating record labels (human-readable
  identifiers).

- **`all_related_label_paths`**: Similar to `all_related_paths`, but only
  includes paths needed for label generation.

##### Resource Functions

- **`sorted_fields_for_ui(dset, resource, fields_list)`**: A function that
  sorts fields for UI display. By default, it returns fields in their defined
  order, but can be customized via the `sf_for_ui` parameter.

- **`read_only_fields`**: A dictionary that defines which fields should be
  read-only in editors. Keys can be:
  - Field name only: `"field_name"` (applies to this field across all
    resources)
  - Resource-qualified: `"resource_name.field_name"` (applies only to this
    specific resource's field)

  Values are dictionaries with optional keys:
  - `"rec_to_str"`: A Python format string used to populate the editor widget.
    It receives a `field` argument with the field name. Default generates
    `self.c_{field}.setText(str(record.{field}) if record else "")`.
  - `"ui_xml"`: XML content for the field widget in the UI file. Default
    creates a read-only QLineEdit.

##### Resource Methods (via `r` object)

- **`r.sorted_fields()`**: Returns fields sorted according to the resource's
  sorting logic.

- **`r.sorted_fields_and_categories()`**: Returns a dictionary mapping category
  names to sorted lists of fields in that category.

- **`r.primary_fields()`**: Returns a list of field names that form the primary
  key.

- **`r.primary_inst_fields()`**: Returns the actual field objects (not just
  names) that form the primary key.

- **`r.label_to_python()`**: Returns Python code (as a string) that generates
  the human-readable label for a record. This is typically used in label field
  implementations.

- **`r[name]`**: Allows accessing fields by name using dictionary-style syntax.
  Returns the field object or raises KeyError if not found.

- **`r.is_connection_resource`**: A boolean property indicating if this
  resource represents a database connection configuration.

- **`r.minimum_field_set()`**: Returns the minimum set of fields needed to
  uniquely identify a record.

### 4. Field-Level Templates

Field-level templates generate files for individual fields within a resource.
They have access to all common variables, all top-level variables, all
category-level variables, all resource-level variables, plus the
field-specific variables below.

#### Field Template Files

- `c/m/field.py.j2`: Generates the field definition class that specifies how
  the field is displayed, filtered, and edited in the UI

#### Available Variables for Field Template Files

##### Field Object Variables

- **`field`**: The field object (`ExField`) itself. This provides access to
  all properties and methods of the field.

- **`FldPascal`**: The field name in PascalCase format (e.g., "FirstName"
  from "first_name"). Used for class names.

- **`fld_snake`**: The field name in snake_case format (e.g., "first_name").
  Used for file names and variable names.

- **`fld_p_snake`**: The plural form of the field name in snake_case. Used in
  some contexts where pluralization is needed.

- **`fld_camel`**: The field name in camelCase format (e.g., "firstName"). Used
  in some variable names.

- **`fld_text`**: A human-readable text name for the field, typically used in
  UI labels.

- **`FldText`**: The capitalized version of `fld_text`, used in titles.

- **`fld_docs`**: The docstring of the field split into lines. This contains
  the description of what the field represents.

- **`fld_bc`**: The base class name for the field type in PascalCase format
  (e.g., "RefManyToOne", "String", "Integer"). This is derived from the field
  type name.

- **`fld_attrs`**: A dictionary containing all attribute values of the field
  object. Keys are attribute names, values are their current values. This is
  used to determine which field attributes differ from their defaults.

- **`fld_is_ref`**: A boolean indicating whether this field is a reference field
  (foreign key or relationship field). True for one-to-one, one-to-many,
  many-to-one, and many-to-many relationships.

##### Field Functions

- **`gfp(field, fld_attrs, fld_bc)`**: A function that generates field parts
  - it returns a generator yielding tuples of `(attribute_name, type_name,
  default_value_string)` for all field attributes that differ from their base
  class defaults. Used to generate only the custom attributes in field class
  definitions.

- **`base_ui_class(field)`**: A function that returns the Qt widget class name
  that should be used for editing this field. By default, it maps field types
  to widget classes (e.g., "string" → "DrfLineEditor", "integer" → "DrfIntEditor",
  "many-to-one" → "Qt{ResourceName}SiSe"). Can be customized via the
  `base_ui_class` parameter.

##### Field Methods (via `field` object)

- **`field.type_name`**: The type name of the field as a string (e.g., "string",
  "integer", "date", "many-to-one", "one-to-many").

- **`field.name`**: The name of the field as defined in the database model.

- **`field.title`**: The human-readable title/label for the field.

- **`field.description`**: The full description text of the field (if
  available).

- **`field.doc_lines`**: The description split into lines (list of strings).

- **`field.primary`**: Boolean indicating if this field is part of the primary
  key.

- **`field.nullable`**: Boolean indicating if this field can have NULL/None
  values.

- **`field.read_only`**: Boolean indicating if this field should be read-only
  in editors.

- **`field.category`**: The category name that this field belongs to (for UI
  organization).

- **`field.fk_to`**: If this is a foreign key field, this is the resource
  object that this field references. None otherwise.

- **`field.fk_from`**: If this field is referenced by other resources, this
  property provides information about those references.

- **`field.ref`**: For reference fields, this is the resource object that the
  field references.

- **`field.enum_values`**: For enum fields, this is a list of tuples
  representing (value, label) pairs for the enum options.

- **`field.multiline`**: For string fields, this boolean indicates if the
  field should use a multi-line text editor.

- **`field.is_ref_type`**: Boolean indicating if this is a reference
  relationship field.

- **`field.is_many_to_many_type`**: Boolean indicating if this is a
  many-to-many relationship.

- **`field.is_one_to_many_type`**: Boolean indicating if this is a one-to-many
  relationship.

- **`field.ref.pascal_case_name`**: When `field.ref` exists, this is the
  PascalCase name of the referenced resource.

- **`field.ref.categories`**: When `field.ref` exists, this is the list of
  categories that the referenced resource belongs to.

- **`field.ref.snake_case_name_plural`**: When `field.ref` exists, this is
  the plural snake_case name of the referenced resource.

- **`field.ref.primary_fields()`**: When `field.ref` exists, this method
  returns the primary key field names of the referenced resource.

- **`field.ref.is_primary_simple`**: When `field.ref` exists, this boolean
  indicates if the referenced resource has a simple (single-field) primary
  key.

- **`field.ref.label_to_python()`**: When `field.ref` exists, this method
  returns Python code that generates the label for records of the referenced
  resource.

- **`field.ref.get_fields_for_ref_filtering()`**: When `field.ref` exists,
  this method returns a list of fields that should be used for filtering and
  searching when selecting referenced records.

##### Field-Specific Functions for Editor UI Template

- **`enum_v2p(enum_values)`**: A function that converts enum values (list of
  tuples) to a property string format. Takes enum values like `[(1, "Option
  1"), (2, "Option 2")]` and converts them to `"1:Option 1,2:Option 2"` for
  use in Qt widget properties.

### Template Usage Examples

#### Example 1: Using Resource Variables

In a resource-level template, you can access resource information like this:

```jinja2
The resource {{ ResPascal }} ({{ res_snake }}) belongs to
{{ categories|join(', ') }} categories and has {{ fields|length }} fields.
```

#### Example 2: Iterating Through Fields

```jinja2
{% for field in fields %}
Field {{ field.name }} is of type {{ field.type_name }}
{% endfor %}
```

#### Example 3: Conditional Logic Based on Primary Key

```jinja2
{% if res_spl_id %}
    return record.{{ res_primaries[0] }}
{% else %}
    return ({{ res_primaries|join(', record.') }})
{% endif %}
```

#### Example 4: Generating Code with Field Attributes

```jinja2
{% for part_name, part_class, part_default in gfp(field, fld_attrs, fld_bc) %}
{{ part_name }}: {{ part_class }} = field(default={{ part_default }})
{% endfor %}
```

### Preserving Custom Content

When templates are regenerated, content between special comment markers is
preserved. Place your custom code between these markers:

```jinja2
# exdrf-keep-start variable_name ----------------------------------------------
Your custom code here
# exdrf-keep-end variable_name ------------------------------------------------
```

The `variable_name` should match one of the preserved content variables
documented above. For example, to add custom imports, use:

```jinja2
# exdrf-keep-start other_imports ----------------------------------------------
from my_custom_module import MyClass
# exdrf-keep-end other_imports -------------------------------------------------
```
