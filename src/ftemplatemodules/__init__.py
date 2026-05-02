"""fTemplateModules - Magically Python importable f-string template files."""

from .registry import add_transform, add_parser  # noqa: F401

# Import transforms and parsers for side-effect registration
# (modules functions register themselves via decorators on import)
from . import transforms  # noqa: F401
from . import parsers  # noqa: F401

# Import and re-export public API
from .codegen import (  # noqa: F401
    loadm,
    unparse,
    set_debug_hook,
    debug_hook,
)

from .importer import install_hook
install_hook()
