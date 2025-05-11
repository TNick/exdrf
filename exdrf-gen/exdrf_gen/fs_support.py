"""The classes in this module help with generating the file and folder
structure. For some of them there is a one-to-one correspondence between
the class and the file that is generated. Other will generate multiple files
based on the content of the dataset, the model categories, list of models and
fields.
"""

import os
from typing import TYPE_CHECKING, Any, Dict, cast

from attrs import define, field
from exdrf_al.calc_q import (
    all_related_label_models,
    all_related_label_paths,
    all_related_models,
    all_related_paths,
)
from jinja2 import Environment

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset  # noqa: F401
    from exdrf.field import ExField  # noqa: F401
    from exdrf.resource import ExResource  # noqa: F401


# CompList = List[Union["File", "Dir"]]
CompList = Any


@define
class Base:
    def create_file(
        self, env: Environment, path: str, name: str, src: str, **kwargs
    ) -> str:
        """Creates a file from the template.

        Args:
            env: The Jinja2 environment to use for rendering the template.
            path: The path to the directory where the file will be created.
            name: The name of the file to be created. Can be a template string.
            src: The name of the template file to be used.
            **kwargs: Additional keyword arguments to pass to the template
                rendering function and the file name.

        Returns:
            The path to the created file.
        """
        assert hasattr(self, "extra"), "extra attribute not set"
        mapping = {**self.extra, **kwargs}  # type: ignore

        template = env.get_template(src)
        os.makedirs(path, exist_ok=True)
        result_file = os.path.join(path, name.format(**mapping))

        with open(result_file, "w", encoding="utf-8") as f:
            f.write(template.render(source_templ=src, **mapping))
        return result_file

    def create_directory(self, path: str, name: str, **kwargs) -> str:
        """Creates a directory.

        Args:
            path: The name of the directory to be created.
            name: The name of the directory to be created. Can be a template
            **kwargs: Additional keyword arguments to pass to the name.

        Returns:
            The path to the created directory.
        """
        assert hasattr(self, "extra"), "extra attribute not set"
        mapping = {**self.extra, **kwargs}  # type: ignore

        result = os.path.join(path, name.format(**mapping))
        os.makedirs(result, exist_ok=True)
        return result

    def generate(self, out_path: str, **kwargs) -> None:
        """Generates the file or directory structure.

        Args:
            out_path: The path to the output directory.
            **kwargs: Additional keyword arguments to pass to the template
                rendering function.
        """
        raise NotImplementedError("generate method not implemented")


@define
class File(Base):
    """A file to be created.

    Creates a single file that receives a context that depends on the parent
    directories.
    """

    name: str = field()
    template: str = field()
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs) -> None:
        env = kwargs.pop("env")
        mapping = {**self.extra, **kwargs}
        self.create_file(env, out_path, self.name, self.template, **mapping)


@define
class Dir(Base):
    """A directory to be created.

    Creates a directory that receives a context that depends on the parent
    directories. The context is passed to all of its children.
    """

    name: str = field()
    comp: CompList = field(factory=list)
    extra: Dict[str, Any] = field(factory=dict)

    def generate(self, out_path: str, **kwargs) -> None:
        mapping = {**self.extra, **kwargs}
        c_path = self.create_directory(out_path, self.name, **mapping)
        for comp in self.comp:
            comp.generate(c_path, **mapping)


def field_base_class(fld: "ExField"):
    f_base_class = "".join([c.title() for c in fld.type_name.split("-")])
    if "To" in f_base_class:
        f_base_class = f"Ref{f_base_class}"
    return f_base_class


def field_to_args(field: "ExField"):
    return {
        "field": field,
        "FldPascal": field.pascal_case_name,
        "fld_snake": field.snake_case_name,
        "fld_p_snake": field.snake_case_name_plural,
        "fld_camel": field.camel_case_name,
        "fld_text": field.text_name,
        "FldText": field.text_name.capitalize(),
        "fld_docs": field.doc_lines,
        "fld_bc": field_base_class(field),
        "fld_attrs": {
            a.name: getattr(field, a.name)
            for a in field.__attrs_attrs__  # type: ignore
        },
        "fld_is_ref": field.is_ref_type,
    }


@define
class FieldFile(File):
    """Creates one file for each field.

    The template will receive field-specific data in the context,
    along with parent model data.
    """

    def generate(self, out_path: str, **kwargs) -> None:
        env = kwargs.pop("env")
        for fld in kwargs["fields"]:
            fld = cast("ExField", fld)
            args = {
                **self.extra,
                **kwargs,
                **field_to_args(fld),
            }
            self.create_file(env, out_path, self.name, self.template, **args)


@define
class FieldDir(Dir):
    """Creates one directory for each field.

    If the field has a ResDir in its parents, one field will be generated
    for each field of the model. If the field has a CategDir in its
    parents, one field will be generated for each field of every model in that
    category. If the field has a TopDir in its parents, one field will be
    generated for each field of every model in every category.

    All of its children will receive field-specific data in the context,
    along with parent model data.
    """

    name: str = field(default="{fld_snake}")

    def generate(self, out_path: str, **kwargs) -> None:
        for fld in kwargs["fields"]:
            fld = cast("ExField", fld)
            args = {
                **self.extra,
                **kwargs,
                **field_to_args(fld),
            }
            c_path = self.create_directory(out_path, self.name, **args)
            for comp in self.comp:
                comp.generate(c_path, **args)


def resource_to_args(resource: "ExResource"):
    return {
        "r": resource,
        "fields": resource.sorted_fields(),
        "categories": resource.categories,
        "fields_cats": resource.sorted_fields_and_categories(),
        "ResPascal": resource.pascal_case_name,
        "res_snake": resource.snake_case_name,
        "res_p_snake": resource.snake_case_name_plural,
        "res_camel": resource.camel_case_name,
        "res_text": resource.text_name,
        "ResText": resource.text_name.capitalize(),
        "res_docs": resource.doc_lines,
        "res_mfs": resource.minimum_field_set(),
        "res_spl_id": resource.is_primary_simple,
        "res_primaries": resource.primary_fields(),
        "all_related_models": all_related_models(resource),
        "all_related_paths": all_related_paths(resource),
        "all_related_label_paths": all_related_label_paths(resource),
        "all_related_label_models": all_related_label_models(resource),
    }


@define
class ResFile(File):
    """Creates one file for each model.

    If the model has a CategDir in its parents, one file will be generated
    for each model in that category. If the model has a TopDir in its
    parents, one file will be generated for each model in every category.

    The template will receive model-specific data in the context
    along with parent dataset data.
    """

    def generate(self, out_path: str, **kwargs) -> None:
        env = kwargs.pop("env")
        for resource in kwargs["resources"]:
            resource = cast("ExResource", resource)
            args = {
                **self.extra,
                **kwargs,
                **resource_to_args(resource),
            }
            self.create_file(env, out_path, self.name, self.template, **args)


@define
class ResDir(Dir):
    """Creates one directory for each model.

    If the model has a CategDir in its parents, one directory will be
    generated for each model in that category. If the model has a TopDir in
    its parents, one directory will be generated for each model in every
    category.

    All of its children will receive model-specific data in the context
    along with parent dataset data.
    """

    name: str = field(default="{res_snake}")

    def generate(self, out_path: str, **kwargs) -> None:
        for resource in kwargs["resources"]:
            resource = cast("ExResource", resource)
            args = {
                **self.extra,
                **kwargs,
                **resource_to_args(resource),
            }
            c_path = self.create_directory(out_path, self.name, **args)
            for comp in self.comp:
                comp.generate(c_path, **args)


@define
class CategFile(File):
    """Creates one file for each model category.

    The template will receive category-specific data, the list of models in
    that category and dataset information.
    """

    def generate(self, out_path: str, **kwargs) -> None:
        dset: "ExDataset" = kwargs["dset"]
        env = kwargs.pop("env")
        for ctg, resources in dset.zero_categories():
            args = {
                **self.extra,
                **kwargs,
                "category_snake": ctg,
                "resources": resources,
            }
            self.create_file(env, out_path, self.name, self.template, **args)


@define
class CategDir(Dir):
    """Creates one directory for each model category.

    All of its children will receive category-specific data, the list of models
    in that category and dataset information.
    """

    name: str = field(default="{category_snake}")

    def generate(self, out_path: str, **kwargs) -> None:
        for ctg, resources in kwargs["categ_zero"]:
            args = {
                **self.extra,
                **kwargs,
                "category_snake": ctg,
                "resources": resources,
            }
            c_path = self.create_directory(out_path, self.name, **args)
            for comp in self.comp:
                comp.generate(c_path, **args)


@define
class TopDir(Dir):
    """Creates the top directory.

    All of its children will receive dataset-specific data.
    """

    name: str = field(init=False, default="")

    def generate(self, out_path: str, **kwargs) -> None:
        """Generates the directory structure and files.

        Args:
            d_set: The dataset to generate the structure for.
            out_path: The path to the output directory.
            **kwargs: Additional keyword arguments to pass to the template
                rendering function.
        """
        assert "dset" in kwargs, "Dataset not provided in kwargs"
        assert "env" in kwargs, "Environment not provided in kwargs"
        dset: "ExDataset" = kwargs["dset"]

        for comp in self.comp:
            args = {
                **self.extra,
                **kwargs,
            }
            comp.generate(
                out_path,
                resources=dset.resources,
                categ_map=dset.category_map,
                categ_zero=dset.zero_categories(),
                resources_sd=dset.sorted_by_deps(),
                **args,
            )
