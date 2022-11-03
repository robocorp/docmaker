"""This invoke task will automatically turn any local Python modules into
an HTML documentation website.
"""
import sys
import os
from inflection import titleize
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
DEFAULT_SOURCE = REPO_ROOT / "source"
DOC_PATH = REPO_ROOT / "docs"
DOC_SOURCE_PATH = DOC_PATH / "source"
COMPONENT_PATH = DOC_PATH / "components"
LIBRARIES_PATH = DOC_SOURCE_PATH / "libraries"
SOURCE_INCLUDES = DOC_SOURCE_PATH / "include"
LIBDOC_PATH = SOURCE_INCLUDES / "libdoc"
LIBDOC_TEMPLATE = DOC_SOURCE_PATH / "template" / "libdoc" / "libdoc.html"
LIBSPEC_PATH = DOC_SOURCE_PATH / "libspec"
JSON_PATH = DOC_SOURCE_PATH / "json"
JSON_MERGE_TARGET = SOURCE_INCLUDES / "latest.json"
PYTHON_MERGE = DOC_SOURCE_PATH / "merge.py"


def _parse_commas(param: List[str]) -> List[str]:
    """Extends a param if comma-separated values were included"""
    out_list = []
    for item in param:
        out_list.extend(item.split(","))
    return out_list


@task(iterable=["include"], aliases=["build", "docs", "build-docs"])
def generate_documentation(
    ctx,
    source_path=None,
    include=None,
    project_title=None,
    language="rfw",
    documentation_format="rest",
):
    """This task generates a documentation website
    for all modules in ``source_path``.

    :param source_path: Optional. Defines a path to source files. All
     files within this path will be parsed for documentation. Defaults
     to local directory ``source`` in robot's root folder.
    :param include: Optional. List of Python modules to parse from
     ``source_path``. If not included, all modules will be parsed for
     documentation. These can be provided using Python dot-notation
     or as paths to the individual source files.
    :param project_title: If provided, the documentation will this
     string as it's main title, otherwise it will Titleize the name
     of the source path's root folder.
    :param language: Defaults to ``rfw`` for Robot Framework. This
     will read the source files as Robot Framework libraries. Allowed
     values are:

     - ``rfw``: interprets modules and classes as Robot Framework
       libraries and generated keyword documentation.
     - ``python``: interprets modules as Python modules and
       documents them as programmatic APIs.

    :param documentation_format: Defaults to ``rest`` as most Python
     libraries are written using restructured text format, but you can
     select alternatives such as ``robot``, ``html``, or ``text``. If a
     library specifies it's documentation format
    """
    source_path = source_path or DEFAULT_SOURCE
    source_path = Path(source_path).resolve()
    if not source_path.is_dir():
        raise ValueError("Source path must be a directory")
    if not source_path.exists():
        raise ValueError("Source path does not exist")
    os.environ["PYTHONPATH"] += f"{os.pathsep}{source_path}"
    print(sys.path)
    source_dir = SourceDirectory(
        source_path,
        documentation_type=language,
        documentation_format=documentation_format,
    )
    if include:
        include = _parse_commas(include)
        for name in include:
            source_dir.load_source_file(name)

    # write the source index file
    title = project_title or source_path.name
    title = f"{titleize(title)} Documentation"
    root_index_component = Component(
        COMPONENT_PATH / "index.rst",
        documentation_type=language,
        documentation_format=documentation_format,
    )
    root_index_component.customize_contents(
        project_title=title, project_title_bar="=" * len(title)
    )
    root_index_component.write(DOC_SOURCE_PATH)

    # build all source doc files from components for each sourcedoc
    for doc in source_dir.source_files:
        file_component = Component(
            COMPONENT_PATH / f"{language.lower()}_library_index.rst",
            documentation_type=language,
            documentation_format=documentation_format,
        )
        title = titleize(doc.name)
        file_component.customize_contents(
            module_name=doc.name, module_title=title, module_title_bar="-" * len(title)
        )
        file_component.write(LIBRARIES_PATH / f"{doc.name}.rst")

        # build libdoc for this source
        ctx.run(
            f"docgen --format html --output {LIBDOC_PATH} "
            f"--template {LIBDOC_TEMPLATE} {doc.name}"
        )
        # build libspec for this source
        ctx.run(
            f"docgen --format libspec --output {LIBSPEC_PATH} "
            f"--no-patches {doc.name}"
        )
        # build json docs for this source
        ctx.run(
            f"docgen --format json-html --output {JSON_PATH} "
            f"--no-patches {doc.name}"
        )

    # merge json
    ctx.run(f"python {PYTHON_MERGE} {JSON_PATH} {JSON_MERGE_TARGET}")

    # build docs
    ctx.run(f"sphinx-build -aE -b html -j auto {DOC_SOURCE_PATH} {OUTPUT}")
