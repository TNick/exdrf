import logging
import os
import re
from os.path import getmtime, isfile, join

from exdrf.utils import inflect_e
from jinja2 import BaseLoader, Environment, TemplateNotFound, select_autoescape

logger = logging.getLogger(__name__)


class Loader(BaseLoader):
    """Jinja loader that loads templates from a set of paths."""

    def __init__(self, path):
        self.paths = []

    def get_source(self, environment, template):
        if isfile(template):
            template_path = template
        else:
            template_path = None
            for path in self.paths:
                candidate_path = join(path, *template.split("/"))
                if isfile(candidate_path):
                    template_path = candidate_path
                    break

        # If the template is not found in any of these paths, raise an error
        if template_path is None:
            raise TemplateNotFound(template)

        # Store the last modified time of the template file
        mtime = getmtime(template_path)

        # Read the template file
        with open(template_path) as f:
            source = f.read()

        # Return the source, template path, and a function to check if the
        # template has changed
        return source, template_path, lambda: mtime == getmtime(template_path)


def create_jinja_env():
    """Creates a base Jinja2 environment for rendering templates."""
    jinja_env = Environment(
        loader=Loader(os.path.dirname(__file__)),
        autoescape=select_autoescape(),
        auto_reload=False,
    )

    # List functions.
    jinja_env.globals["len"] = lambda x: len(x)
    jinja_env.globals["sorted"] = lambda x: sorted(x)
    jinja_env.globals["enumerate"] = lambda x: enumerate(x)
    jinja_env.globals["len_range"] = lambda x: range(len(x))

    # Containers.
    jinja_env.globals["list"] = list
    jinja_env.globals["set"] = set
    jinja_env.globals["dict"] = dict

    # String utilities.
    jinja_env.globals["pluralize"] = lambda x: inflect_e.plural(x)
    jinja_env.globals["snake_pl"] = lambda x: inflect_e.plural(
        re.sub(r"(?<!^)(?=[A-Z])", "_", x).lower()  # type: ignore
    )
    jinja_env.globals["snake"] = lambda x: re.sub(
        r"(?<!^)(?=[A-Z])", "_", x
    ).lower()

    # Tests.
    jinja_env.tests["None"] = lambda value: value is None
    return jinja_env


jinja_env = create_jinja_env()
