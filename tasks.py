"""This invoke task will automatically turn any local Python modules into
an HTML documentation website.
"""
import sys
from typing import List
from invoke import task
from pathlib import Path
from importlib import __import__

# custom classes
from documenter import Component, SourceDoc, SourceDirectory

# shell constants
SPHINX = "sphinx-build"
DOCGEN = "docgen"

# Path constants
REPO_ROOT = Path(__file__).parent.resolve()
OUTPUT = REPO_ROOT / "output"
DOC_PATH = REPO_ROOT / "docs"
SOURCE_PATH = DOC_PATH / "source"
COMPONENT_PATH = DOC_PATH / "components"


def _find_modules(path):
    """Finds all module files in provided path."""
    found_paths = Path(path).glob("*.py")
    return [f for f in found_paths if f.is_file()]


def _get_class_names(classes: List[str] = None):
    """Checks if the provided classes have ``.`` in them and if so,
    turns them into a tuples of ``(module,class)``
    """
    output = []
    for klass in classes:
        if "." in klass:

            output.append(())


def _import_mods(classes: List[str] = None):
    """Attempt to import the classes provided."""
    # TODO: Do we need this function? Sphinx autodoc will import the module.
    if not isinstance(classes, list):
        classes = list(classes)
    source_classes = []
    for klass in classes:
        try:
            source_classes.append(__import__())
        except ImportError:
            pass


def _parse_commas(param: List[str]) -> List[str]:
    """Extends a param if comma-separated values were included"""
    out_list = []
    for item in param:
        out_list.extend(item.split(","))
    return out_list


def _generate_library_strings(modules: List[str]) -> str:
    """Generates REST formatted strings for each provided module."""
    pass


def _generate_index_rst(modules: List[str]) -> None:
    """Generates the index.rst in /source"""


@task(iterable=["include", "class"])
def generate_documentation(ctx, source_path, include, language="rfw"):
    """This task generates a documentation website
    for all modules in ``source_path``.

    :param source_path: Defines a path to source files. All files
     within this path will be parsed for documentation.
    :param include: Optional. List of Python modules to parse from
     ``source_path``. If not included, all modules will be parsed for
     documentation.
    :param language: Defaults to ``rfw`` for Robot Framework. This
     will read the source files as Robot Framework libraries. Allowed
     values are:

     - ``rfw``: interprets modules and classes as Robot Framework
       libraries and generated keyword documentation.
     - ``python``: interprets modules as normal Python modules and
       documents them as programmatic APIs.
    """

    """TODO:
    May not need to import the modules to perform this work.

    For the happy path: 

     - Get names of all .py files.
     - run docgen with a or glob for each py file name or run
       docgen once for each py file.
     - Create template rst files for each py file where it does
       an automodule of that file. These files live in a new
       ``libs`` directory in source.
     - Use a toctree directive in the index to include all rst
       files from ``libs``.

    If the py file does not have classes in it, automodule should
    still handle it, but docgen may fail.
    
    """
    sys.path.append(Path(source_path))
    source_dir = SourceDirectory(source_path)
    if include:
        include = _parse_commas(include)
