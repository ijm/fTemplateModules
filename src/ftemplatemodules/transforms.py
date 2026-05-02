"""Built-in template transforms."""

import pyparsing as pp
from .registry import add_transform


@add_transform("remove_cpp_comments")
def _(tmpl: str, docs: str) -> tuple[str, str]:
    """Use PyParsing's cpp_style_comment() to remove c++ style comments"""
    return (pp.cpp_style_comment().suppress().transformString(tmpl), docs)


@add_transform("remove_python_comments")
def _(tmpl: str, docs: str) -> tuple[str, str]:
    """Remove Python-style comments using PyParsing's python_style_comment()"""
    return (pp.python_style_comment().suppress().transformString(tmpl), docs)


@add_transform("remove_html_comments")
def _(tmpl: str, docs: str) -> tuple[str, str]:
    """Use PyParsing's html_comment() to remove html style comments"""
    return (pp.html_comment().suppress().transformString(tmpl), docs)


@add_transform("append_doc")
def _(tmpl: str, docs: str) -> tuple[str, str]:
    """Append the current template string to the current doc string."""
    return (tmpl, docs + tmpl)


@add_transform("unwrap_lines")
def _(tmpl: str, docs: str) -> tuple[str, str]:
    """
    Unwrap line-broken lines and normalize line white space.
    This transform reduces the number of EOLs in a row and replaces
    an EOL with a space if it is the only one.
    """
    @pp.OneOrMore(pp.lineEnd()).set_parse_action
    def newlines(_s: str, _loc: int, tokens: pp.ParseResults):
        return [" "] if len(tokens) == 1 else tokens[1:]

    return (newlines.transformString(tmpl), docs)


@add_transform("latex_tmpl")
def _(tmpl: str, docs: str) -> tuple[str, str]:
    """Transform for Latex Templates to escape {} to {{}} and map <> to {}"""

    def replace(elem, target: str):
        @elem.set_parse_action
        def _(_s: str, _loc: int, _tokens: pp.ParseResults):
            return [target]
        return elem

    transform = (replace(pp.Char("{"), "{{") |
                 replace(pp.Char("}"), "}}") |
                 replace(pp.Char("<"), "{") |
                 replace(pp.Char(">"), "}"))

    return (transform.transformString(tmpl), docs)
