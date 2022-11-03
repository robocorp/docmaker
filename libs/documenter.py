"""This library provides classes that can be used to generate sphinx source docs"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from string import Formatter
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec

VALID_DOC_TYPES = ["python", "rfw"]
VALID_DOC_FORMATS = ["robot", "html", "text", "rest"]
SOURCE_LANGUAGES = {".py": "python", ".robot": "rfw", ".resource": "rfw"}

PathLike = Union[Path, str]


class Source:
    """Represents source used to build library documentation"""

    def __init__(
        self,
        *args,
        documentation_type: Optional[str] = None,
        documentation_format: Optional[str] = None,
        **kwargs,
    ) -> None:
        if (
            documentation_type is not None
            and str(documentation_type).lower() not in VALID_DOC_TYPES
        ):
            raise ValueError(
                f"The provided documentation_type of '{documentation_type}' is not "
                f"valid, must be one of {VALID_DOC_TYPES}"
            )
        self.documentation_type: Optional[str] = documentation_type or "rfw"
        if (
            documentation_format is not None
            and str(documentation_format).lower() not in VALID_DOC_FORMATS
        ):
            raise ValueError(
                f"The provided documentation_format of '{documentation_format}' is not "
                f"valid, must be one of {VALID_DOC_FORMATS}"
            )
        self.documentation_format: Optional[str] = documentation_format or "REST"
        self.path: Path = Path(*args, **kwargs)

    def partition_source_name(self, name: str) -> Tuple[str, str]:
        """Returns a tuple of the Parent source name and the source name

        This function assumes Python conventions for source naming.
        """
        parent_name, _, source_name = name.rpartition(".")
        return parent_name, source_name


class SourceFile(Source):
    """Represents a source file used to build library documentation"""

    def __init__(
        self,
        *args,
        documentation_type: Optional[str] = None,
        documentation_format: Optional[str] = None,
        **kwargs,
    ) -> None:
        self._content: Optional[str] = None
        super().__init__(
            *args,
            documentation_type=documentation_type,
            documentation_format=documentation_format,
            **kwargs,
        )

    @property
    def content(self) -> str:
        """Reads contents from disk, stores it as a property and returns it"""
        if self._content is None:
            self._content = self.path.read_text()
        return self._content


class Component(SourceFile):
    """A source documentation component, which must be formatted before
    being written as doc source.
    """

    def __init__(
        self,
        *args,
        documentation_type: Optional[str] = None,
        documentation_format: Optional[str] = None,
        target_path: Optional[PathLike] = None,
        **kwargs,
    ) -> None:
        self.target_path = target_path
        super().__init__(
            *args,
            documentation_type=documentation_type,
            documentation_format=documentation_format,
            **kwargs,
        )

    def _append_file_name(self, new_path: PathLike):
        """Adds the current filename to the path if path is not a file"""
        new_path = Path(new_path)
        if not new_path.is_file() and new_path.is_dir():
            return new_path / self.path.name
        else:
            return new_path

    @property
    def target_path(self) -> Path:
        """The component's target path so it can be used to generate docs"""
        return self._target

    @target_path.setter
    def target_path(self, value: Union[PathLike, None]):
        if value is None:
            self._target = Path(".")
        else:
            self._target: Path = self._append_file_name(value)

    def write(self, target: PathLike = None) -> None:
        """Write the contents to disk"""
        target = Path(target)
        if not target.is_file():
            target = self._append_file_name(target)
        if not target.parent.exists():
            target.parent.mkdir(parents=True)
        with target.open("w") as file:
            file.write(self.content)

    def customize_contents(self, *args, **kwargs):
        """Formats the content with provided args and kwargs.

        This function uses the ``format`` method for strings to
        format the contents as a template.
        """
        self._content = self.content.format(*args, **kwargs)

    def get_template_fields(self):
        """Returns a list of the fields available within the contents which
        can be customized.
        """
        return [fname for _, fname, _, _ in Formatter.parse(self._content) if fname]


class SourceDoc(SourceFile):
    """A piece of code source that needs to be converted to HTML documentation"""

    def __init__(
        self,
        *args,
        documentation_type: Optional[str] = None,
        documentation_format: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            *args,
            documentation_type=documentation_type,
            documentation_format=documentation_format,
            **kwargs,
        )
        self._name: Optional[str] = None
        self._source_lan: Optional[str] = None

    @property
    def name(self) -> str:
        """Name of the module or source doc"""
        if self._name is None:
            if self.path.stem == "__init__":
                name_to_use = self.path.parent.stem
            else:
                name_to_use = self.path.stem
            self._name = name_to_use
        return self._name

    @property
    def source_language(self) -> str:
        """The language this source doc is written in based on its suffix"""
        if self._source_lan is None:
            self._source_lan = SOURCE_LANGUAGES[self.path.suffix]
        return self._source_lan


class SourceDirectory(Source):
    """A directory to be searched for source documentation which will be
    parsed into documentation
    """

    def __init__(
        self,
        *args,
        documentation_type: Optional[str] = None,
        documentation_format: Optional[str] = None,
        **kwargs,
    ) -> None:
        self._source_files: Optional[List[SourceDoc]] = None
        super().__init__(
            *args,
            documentation_type=documentation_type,
            documentation_format=documentation_format,
            **kwargs,
        )

    def _get_init_path_for_dir(self, path: PathLike) -> Path:
        """Gets the path to the ``__init__`` file at the indicated directory path.

        If no __init__ file exists, returns the directory.
        """
        dir_path = Path(path)
        python_path = dir_path / "__init__.py"
        robot_path = dir_path / "__init__.robot"
        if python_path.exists():
            return python_path
        elif robot_path.exists():
            return robot_path
        else:
            return dir_path

    def convert_name_to_path(self, name: str) -> Path:
        """Converts a name to a path assuming the name may include
        a ``.`` to indicate relative naming compared to path sep.
        """
        count_dot_seps = name.count(".")
        if count_dot_seps > 0:
            if name[0] == ".":
                return self.convert_name_to_path(name[1:])
            else:
                return Path(name.replace(".", "/", count_dot_seps - 1))
        else:
            possible_path = Path(name)
            if possible_path.is_dir():
                return self._get_init_path_for_dir(possible_path)
            else:
                return possible_path

    def load_source_file(self, name: Union[str, PathLike]):
        """Loads the provided source file from within the source directory

        Relative names to the this source directory's root can be provided
        and names can be provided as paths or using python dot-notation.
        """
        new_sourcedoc = SourceDoc(name)
        if not new_sourcedoc.path.exists():
            new_sourcedoc = SourceDoc(self.convert_name_to_path(name))
        elif new_sourcedoc.path.is_dir():
            new_sourcedoc = SourceDoc(self._get_init_path_for_dir(name))
        if new_sourcedoc.path.is_file():
            if self._source_files is None:
                self._source_files = [new_sourcedoc]
            else:
                self._source_files.append(new_sourcedoc)

    @property
    def source_files(self) -> List[SourceDoc]:
        """The list of source files from the directory. If not yet loaded,
        it will load them first.
        """
        if self._source_files is None:
            raw_files = self.path.glob("**/*")
            self._source_files = [
                SourceDoc(
                    f,
                    documentation_type=self.documentation_type,
                    documentation_format=self.documentation_format,
                )
                for f in raw_files
                if getattr(f, "suffix") in SOURCE_LANGUAGES.keys()
            ]

        return self._source_files
