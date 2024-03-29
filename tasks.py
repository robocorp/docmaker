"""This invoke task will automatically turn any local Python modules into
an HTML documentation website.
"""
import re
import platform
import os
import shutil
import yaml
from inflection import titleize
from typing import List, Dict
from invoke import task
from pathlib import Path
from glob import glob
from bs4 import BeautifulSoup

# custom classes
from documenter import Component, SourceDirectory, PathLike

# shell constants
SPHINX = "sphinx-build"
DOCGEN = "docgen"

# Path constants
REPO_ROOT = Path(__file__).parent.resolve()
OUTPUT = REPO_ROOT / "output"
DOCMAKER_LIB = REPO_ROOT / "libs"
DEFAULT_SOURCE = REPO_ROOT / "source"
DOC_PATH = REPO_ROOT / "docs"
DOC_SOURCE_PATH = DOC_PATH / "source"
COMPONENT_PATH = DOC_PATH / "components"
LIBRARIES_PATH = DOC_SOURCE_PATH / "libraries"
SOURCE_INCLUDES = DOC_SOURCE_PATH / "include"
LIBDOC_PATH = SOURCE_INCLUDES / "libdoc"
LIBDOC_TEMPLATE = DOC_SOURCE_PATH / "template" / "libdoc" / "libdoc.html"
IFRAME_SCRIPT_PATH = (
    DOC_SOURCE_PATH / "template" / "lib" / "iframeResizer.contentWindow.min.js"
)
IFRAMERESIZER_MAP = DOC_SOURCE_PATH / "template" / "iframeResizer.contentWindow.map"
LIBSPEC_PATH = DOC_SOURCE_PATH / "libspec"
JSON_PATH = DOC_SOURCE_PATH / "json"
JSON_MERGE_TARGET = SOURCE_INCLUDES / "latest.json"
PYTHON_MERGE = DOC_SOURCE_PATH / "merge.py"
MY_CONDA = REPO_ROOT / "conda.yaml"
MY_ROBOT = REPO_ROOT / "robot.yaml"
TEMP_DIR = REPO_ROOT / "temp"
TEMP_CONDA = REPO_ROOT / "temp_conda.yaml"
TEMP_ROBOT = REPO_ROOT / "temp_robot.yaml"

CLEAN_PATTERNS = [
    "temp",
    "output",
    "rcc.exe",
    "temp_*.yaml",
    "docs/source/json",
    "docs/source/libspec",
    "docs/source/index.rst",
    "docs/source/libraries/*.rst",
    "docs/source/include/libdoc",
    "docs/source/include/latest.json",
]


def _parse_commas(param: List[str]) -> List[str]:
    """Extends a param if comma-separated values were included"""
    out_list = []
    for item in param:
        out_list.extend(item.split(","))
    return out_list


def _get_source_path(source_path=None):
    """Attempts to get the source path provided or selects the proper
    default.
    """
    source_path = source_path or DEFAULT_SOURCE
    source_path = Path(source_path).resolve()
    if not source_path.is_dir():
        raise ValueError("Source path must be a directory")
    if sum(1 for _ in source_path.iterdir()) == 1:
        return REPO_ROOT.parent.resolve()
    else:
        return source_path


def _merge_lists(original_list: List, other_list: List):
    original_list.extend(
        [
            str(item)
            for item in other_list
            if (isinstance(item, str) or isinstance(item, Path))
            and str(item).lower() not in original_list
        ]
    )


def _merge_path_lists(original_list: List, other_list: List, other_path: PathLike):
    other_path = Path(other_path)
    other_paths = []
    for path in other_list:
        other_paths.append((other_path.parent / path).resolve())
    _merge_lists(original_list, other_paths)


def _merge_yaml(original_yaml: Dict, other_yaml: Dict, other_yaml_path: PathLike):
    other_yaml_path = Path(other_yaml_path)
    if other_yaml.get("PATH", False):
        _merge_path_lists(original_yaml["PATH"], other_yaml["PATH"], other_yaml_path)
    if other_yaml.get("PYTHONPATH", False):
        _merge_path_lists(
            original_yaml["PYTHONPATH"], other_yaml["PYTHONPATH"], other_yaml_path
        )
    if other_yaml.get("dependencies", False):
        _merge_lists(original_yaml["dependencies"], other_yaml["dependencies"])

        for d in [i for i in other_yaml["dependencies"] if isinstance(i, dict)]:
            if d.get("pip", False):
                orig_pip = [
                    i
                    for i in original_yaml["dependencies"]
                    if isinstance(i, dict)
                    and getattr(i, "get", lambda x, y: False)("pip", False)
                ][0]
                _merge_lists(orig_pip["pip"], d["pip"])


def _merge_config_files(source_path: PathLike = None, robot_file: PathLike = None):
    """Attempts to merge the source directory's conda.yaml and robot.yaml
    with this project's files so code documentation can be built.
    """
    robot_path = robot_file or "robot.yaml"
    if not Path(robot_path).is_file():
        raise ValueError("The source robot file path must be a file")

    source_robot_path = Path(source_path) / robot_path
    source_robot_yaml = yaml.safe_load(source_robot_path.read_text())

    source_conda_path = Path(source_path) / str(source_robot_yaml["condaConfigFile"])
    source_conda_yaml = yaml.safe_load(source_conda_path.read_text())

    my_robot_yaml = yaml.safe_load(MY_ROBOT.read_text())
    my_conda_yaml = yaml.safe_load(MY_CONDA.read_text())

    _merge_yaml(my_robot_yaml, source_robot_yaml, source_robot_path)
    _merge_yaml(my_conda_yaml, source_conda_yaml, source_conda_path)

    my_robot_yaml["condaConfigFile"] = str(TEMP_CONDA.name)
    my_robot_yaml.pop("environmentConfigs")

    if not TEMP_DIR.exists():
        TEMP_DIR.mkdir(exist_ok=True)

    with TEMP_CONDA.open("w") as file:
        yaml.dump(my_conda_yaml, file, default_flow_style=False)

    with TEMP_ROBOT.open("w") as file:
        yaml.dump(my_robot_yaml, file, default_flow_style=False)


def _download_rcc(ctx):
    if platform.system() == "Windows":
        ctx.run(
            "curl -o rcc.exe https://downloads.robocorp.com/rcc/releases/latest/windows64/rcc.exe"
        )
        return ".\\rcc.exe"
    if platform.system() == "Linux":
        ctx.run(
            "curl -o rcc https://downloads.robocorp.com/rcc/releases/latest/linux64/rcc"
        )
        ctx.run("chmod a+x rcc")
        return "./rcc"
    if platform.system() == "Darwin":
        ctx.run(
            "curl -o rcc https://downloads.robocorp.com/rcc/releases/latest/macos64/rcc"
        )
        ctx.run("chmod a+x rcc")
        return "./rcc"


def _iframeresizer_script():
    with IFRAME_SCRIPT_PATH.open("r") as script:
        return script.read()


@task(iterable=["include", "exclude"], aliases=["build", "docs", "build-docs"])
def generate_documentation(
    ctx,
    source_path=None,
    source_robot=None,
    include=None,
    exclude=None,
    project_title=None,
    copyright_info=None,
    author_name=None,
    language="rfw",
    in_project=False,
):
    """This task generates a documentation website
    for all modules in ``source_path``.

    You can also set these parameters via the config file ``docmaker_config.yaml``,
    but if both command line and config file is used, command line takes
    precedence.

    :param source_path: Optional. Defines a path to source files. All
     files within this path will be parsed for documentation. Defaults
     to local directory ``source`` in robot's root folder, or the
     parent of the robot's root folder, if local ``source`` is empty.
    :param source_robot: Optional. Defines the ``robot.yaml`` file to
     reference from the provided source path. Defaults to ``robot.yaml``.
    :param include: Optional. List of source files to parse from
     ``source_path``. If not included, all source files will be parsed for
     documentation. These can be provided using Python dot-notation
     or as paths to the individual source files. They must be relative
    to ``source-path``.
    :param exclude: Optional. List of source files to be excluded
     from parsing. These can be provided using Python dot-notation
     or as paths to the individual source files.
    :param project_title: If provided, the documentation will use this
     string as it's main title, otherwise it will Titleize the name
     of the source path's root folder.
    :param copyright_info: If provided, the documentation will use this
     string as the copyright information string in output. If not
     provided, no copyright information will be included.
    :param author_name: If provided, the documentation will use this
     string as the author's name in output, otherwise, no author info
     will be provided.
    :param language: Defaults to ``rfw`` for Robot Framework. This
     will read the source files as Robot Framework libraries. Allowed
     values are:

     - ``rfw``: interprets modules and classes as Robot Framework
       libraries and generated keyword documentation.
     - ``python``: interprets modules as Python modules and
       documents them as programmatic APIs.

    :param in_project: Default to False. Set to True if you are invoking
     this package from inside your own robot/project and have installed
     all of this project's dependencies in your own conda.yaml.
    """
    yaml_config = _parse_yaml_config()
    try:
        source_path = source_path or yaml_config.get("source_path")
        source_robot = source_robot or yaml_config.get("source_robot")
        include = include or yaml_config.get("include")
        exclude = exclude or yaml_config.get("exclude")
        project_title = project_title or yaml_config.get("project_title")
        copyright_info = copyright_info or yaml_config.get("copyright_info")
        author_name = author_name or yaml_config.get("author_name")
        language = language or yaml_config.get("language")
        in_project = in_project or yaml_config.get("in_project") or False
    except AttributeError:
        pass
    source_path = _get_source_path(source_path)
    if not in_project:
        _merge_config_files(source_path, source_robot)
        rcc_exe = _download_rcc(ctx)
        args = []
        if source_path is not None:
            args.append(f'--source-path "{source_path}"')
        if len(include) > 0:
            args.append(f'--include "{",".join(include)}"')
        if len(exclude) > 0:
            args.append(f'--exclude "{",".join(exclude)}"')
        if project_title is not None:
            args.append(f'--project-title "{project_title}"')
        if copyright_info is not None:
            args.append(f'--copyright-info "{copyright_info}"')
        if author_name is not None:
            args.append(f'--author-name "{author_name}"')
        ctx.run(
            f'{rcc_exe} run --space metarobot --robot "{TEMP_ROBOT}" '
            f'--task "Build documentation" --'
            f" --language {language}"
            f" --in-project {' '.join(args)}",
            echo=True,
        )
    else:
        os.environ["PYTHONPATH"] += f"{os.pathsep}{source_path}"
        source_dir = SourceDirectory(
            source_path,
            documentation_type=language,
        )
        if include:
            include = _parse_commas(include)
            for name in include:
                source_dir.load_source_file(name)

        exclude = _parse_commas(exclude)
        exclude.append(REPO_ROOT)
        exclude.append(source_path / "tasks.robot")
        for name in exclude:
            source_dir.exclude_source_file(name)

        # I hate this but this will re-add anything included by
        # the user
        if include:
            for name in include:
                source_dir.load_source_file(name)

        # write the source index file
        root_title = project_title or source_path.name
        root_title = f"{titleize(root_title)} Documentation"
        root_index_component = Component(
            COMPONENT_PATH / "index.rst",
            documentation_type=language,
        )
        root_index_component.customize_contents(
            project_title=root_title, project_title_bar="=" * len(root_title)
        )
        root_index_component.write(DOC_SOURCE_PATH)

        # build all source doc files from components for each sourcedoc
        for doc in source_dir.source_files:
            if doc.source_language == "python":
                file_component = Component(
                    COMPONENT_PATH / f"{language.lower()}_library_index.rst",
                    documentation_type=language,
                )
                title = titleize(doc.name)
                file_component.customize_contents(
                    module_name=doc.name,
                    module_title=title,
                    module_title_bar="-" * len(title),
                )
                file_component.write(LIBRARIES_PATH / f"{doc.name}.rst")

                # build libdoc for this source
                ctx.run(
                    f'docgen --format html --output "{LIBDOC_PATH}" '
                    f'--template "{LIBDOC_TEMPLATE}" {doc.name}'
                )
                # build libspec for this source
                ctx.run(
                    f'docgen --format libspec --output "{LIBSPEC_PATH}" '
                    f'--no-patches {doc.name}'
                )
                # build json docs for this source
                ctx.run(
                    f'docgen --format json-html --output "{JSON_PATH}" '
                    f'--no-patches {doc.name}'
                )
            elif doc.source_language == "rfw":
                file_component = Component(
                    COMPONENT_PATH / f"rfw_library_no_api_index.rst",
                    documentation_type=language,
                )
                title = titleize(doc.name)
                file_component.customize_contents(
                    module_name=doc.name,
                    module_title=title,
                    module_title_bar="-" * len(title),
                )
                file_component.write(LIBRARIES_PATH / f"{doc.name}.rst")

                # build libdoc
                libdoc_output_path = LIBDOC_PATH / doc.path.with_suffix(".html").name
                ctx.run(f'libdoc "{doc.path}" "{libdoc_output_path}"')
                with libdoc_output_path.open("r+") as out_libdoc:
                    libdoc_soup = BeautifulSoup(out_libdoc, "html.parser")
                    script_tag = libdoc_soup.new_tag("script", type="text/javascript")
                    script_tag.string = _iframeresizer_script()
                    sibling = libdoc_soup.find(
                        "script", string=re.compile(r"jQuery Highlight plugin")
                    )
                    sibling.insert_after(script_tag)
                    out_libdoc.write(str(libdoc_soup))
                # build libspec
                ctx.run(
                    f'libdoc "{doc.path}" "{LIBSPEC_PATH / doc.path.with_suffix(".libspec").name}"'
                )
                # build json
                ctx.run(
                    f'libdoc "{doc.path}" "{JSON_PATH / doc.path.with_suffix(".json").name}"'
                )

        # Copy iframe resizer into libdoc source
        shutil.copy2(IFRAMERESIZER_MAP, LIBDOC_PATH / IFRAMERESIZER_MAP.name)
        # merge json
        ctx.run(f'python "{PYTHON_MERGE}" "{JSON_PATH}" "{JSON_MERGE_TARGET}"')

        # create conf overrides
        overrides = [f'-D project="{root_title}"']
        if copyright_info is not None:
            overrides.append(f'-D copyright="{copyright_info}"')
        if author_name is not None:
            overrides.append(f'-D author="{author_name}"')

        # build docs
        ctx.run(
            f"sphinx-build -aE -b html -j auto {' '.join(overrides)} "
            f'"{DOC_SOURCE_PATH}" "{OUTPUT}"',
            echo=True,
        )


def _parse_yaml_config(path="docmaker_config.yaml"):
    yaml_path = Path(path)
    try:
        with yaml_path.open("r") as file:
            return yaml.safe_load(file)
    except Exception:
        return None


@task
def parse_yaml_config_and_run(ctx, path="docmaker_config.yaml"):
    """This task parses the ``docmarker_config.yaml`` file in place
    of command line parameters and generates documentation.
    """
    config = _parse_yaml_config(path)
    generate_documentation(ctx, **config)


@task
def clean(ctx):
    """Cleans the local repository folder of build artifacts."""
    for pattern in CLEAN_PATTERNS:
        for path in glob(pattern, recursive=True):
            print(f"Removing: {path}")
            shutil.rmtree(path, ignore_errors=True)
            try:
                os.remove(path)
            except OSError:
                pass
