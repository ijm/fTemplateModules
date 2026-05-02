"""fTemplateModules - Magically Python importable f-string template files."""

# Import and re-export public API
from .registry import add_transform, add_parser  # noqa: F401
from .codegen import (  # noqa: F401
    loadm,
    unparse,
    set_debug_hook,
    debug_hook,
)

# Import and install the import hook
from .importer import install_hook
install_hook()
