"""This library provides classes that can be used to generate sphinx source docs"""
from pathlib import Path
from typing import Dict, List, Optional, Union
from string import Formatter
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec


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
        self.documentation_type: Optional[str] = documentation_type or "rfw"
        self.format: Optional[str] = documentation_format or "REST"
        self.path: Path = Path(*args, **kwargs)


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
        self.target_path: Path = Path(target_path)
        super().__init__(
            *args,
            documentation_type=documentation_type,
            documentation_format=documentation_format,
            **kwargs,
        )

    @property
    def target_path(self):
        """The component's target path so it can be used to generate docs"""
        return self._target

    @target_path.setter
    def target_path(self, value: PathLike):
        self._target = Path(value)

    def write(self, target: PathLike = None):
        """Write the contents to disk"""

    def customize_contents(self, *args, **kwargs):
        """Formats the content with provided args and kwargs.

        This function uses the ``format`` method for strings to
        format the contents as a template.
        """
        self._content = self._content.format(*args, **kwargs)

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
        self._imp_module = None

    def _import_module(self):
        """Tries to import the module"""
        if self.path.stem == "__init__":
            module_name = self.path.parent.name
        else:
            module_name = self.path.stem
        try:
            loader = SourceFileLoader(module_name, str(self.path.absolute()))
            spec = spec_from_loader(module_name, loader)
            self._imp_module = module_from_spec(spec)
            loader.exec_module(self._imp_module)
        except (ImportError, FileNotFoundError) as e:
            print(
                f"The module at {self.path} could not be imported due to the "
                f"following error: \n{e.msg}"
            )

    @property
    def imported_module(self):
        """The underlying module associated with this source imported as a local module"""
        if self._imp_module is None:
            self._import_module()
        return self._imp_module


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

    @property
    def source_files(self):
        """The list of source files from the directory. If not yet loaded,
        it will load them first.
        """
        if self._source_files is None:
            raw_files = self.path.glob("**/*")
            self._source_files = [
                SourceDoc(
                    f,
                    documentation_type=self.documentation_type,
                    documentation_format=self.format,
                )
                for f in raw_files
                if getattr(f, "suffix") in [".py", ".robot", ".resource"]
            ]

        return self._source_files
