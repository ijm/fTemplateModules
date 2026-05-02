"""Import machinery for .ftmpl files."""

import sys
from pathlib import Path
from importlib.machinery import ModuleSpec, SourcelessFileLoader
import importlib.util

from .codegen import assemble
from .grammar import parse_file


class fTemplateLoader(SourcelessFileLoader):
    def is_package(self, _fullname):
        return False

    def get_code(self, fullname):
        """Load and compile the module code"""

        with open(self.path, "rt", encoding="utf-8") as fd:
            cst = parse_file(fd)
        return compile(assemble(cst), self.path, 'exec')


class fTemplateFinder:
    SUFFIX = ".ftmpl"

    def find_spec(self, name: str, path, _target) -> ModuleSpec:
        """Look for name.ftmpl in the provided search path."""

        search_paths = [path] if isinstance(path, str) else (path or sys.path)
        filename = f"{name}{self.SUFFIX}"
        for base in search_paths:
            candidate = Path(base) / filename
            if candidate.is_file():
                loader = fTemplateLoader(name, str(candidate))
                return importlib.util.spec_from_loader(name, loader)
        return None


def install_hook():
    """Register the .ftmpl import hook. Idempotent."""
    finder = fTemplateFinder()
    if not any(isinstance(f, fTemplateFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, finder)
