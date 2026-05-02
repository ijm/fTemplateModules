"""Import machinery for .ftmpl files."""

import sys
from pathlib import Path
from importlib.machinery import ModuleSpec, SourcelessFileLoader
import importlib.util

from .codegen import assemble
from .grammar import parse_file


class fTemplateLoader(SourcelessFileLoader):
    SUFFIX = ".ftmpl"

    def is_package(self, _fullname):
        return False

    def get_code(self, fullname):
        """Load and compile the module code"""
        path = Path(fullname).with_suffix(self.SUFFIX)

        with open(path, "rt", encoding="utf-8") as fd:
            cst = parse_file(fd)

        return compile(assemble(cst), path.resolve(), 'exec')


class fTemplateFinder:
    def find_spec(self, name: str, path: str, _target) -> ModuleSpec:
        """Look for a toplevel file with ending in `modulesuffix` (.ftmpl)"""

        loader = fTemplateLoader(name, path)
        if Path(name).with_suffix(loader.SUFFIX).is_file():
            return importlib.util.spec_from_loader(name, loader)
        return None


def install_hook():
    """Register the .ftmpl import hook. Idempotent."""
    finder = fTemplateFinder()
    if not any(isinstance(f, fTemplateFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, finder)
