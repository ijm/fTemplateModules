"""Built-in template parsers."""

import ast
from .registry import add_parser


@add_parser("str")
def parse_as_f(tmpl: str) -> ast.expr:
    """Parse template as f-string (rf prefix for raw f-string)."""
    return ast.parse(f'rf"""{tmpl}"""').body[0].value


# Register t-string parser only if t-strings are available (Python 3.14+)
if hasattr(ast, 'TemplateStr'):
    @add_parser("Template")
    def parse_as_t(tmpl: str) -> ast.expr:
        """Parse template as t-string (rt prefix for raw t-string)."""
        return ast.parse(f'rt"""{tmpl}"""').body[0].value
