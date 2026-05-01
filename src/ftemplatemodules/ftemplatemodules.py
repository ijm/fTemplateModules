from typing import Callable
from dataclasses import dataclass, field
import sys
import ast
from pathlib import Path
from importlib.machinery import ModuleSpec, SourcelessFileLoader
import importlib
import pyparsing as pp
# from importlib.util import spec_from_loader
# from importlib import module


# Transforms section
#
# Define optional transforms, and assemble them into a dictionary.
# This is implemented as separate decorated functions rather than a
# dictionary of lambdas.
# The decorator takes the name of the option as seen in the template as
# its only argument and adds the associated function under that name.
# transforms are always of the form (str, str)->(str, str) where the first
# string is the template string, and the second string is the doc-string

@dataclass
class _State:
    """Module-level state container for transforms and configuration."""
    transforms: dict[str, Callable[[str, str], tuple[str, str]]] = field(
        default_factory=dict)
    debug_hook: Callable[[str, str], None] | None = None
    # Future: backend_map: dict[str, Any] = field(default_factory=dict)


# Module singleton
_STATE = _State()


def add_transform(key: str):
    """Curried decorator to add a template to the options dictionary."""
    def f(func: Callable[[str, str], tuple[str, str]]) -> None:
        _STATE.transforms[key] = func
    return f


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


# Parser section.
class Statements:
    IMPORT = 1
    SIG = 2


def get_ftmplgrammar():
    def wrap_tag(elem, tag: int):
        """Flatten and tag a command element with a line number"""
        def h(s: str, lk: int, t: pp.ParseResults):
            return [(tag, pp.lineno(lk, s), " ".join(t))]
        return elem.set_parse_action(h)

    eol = pp.LineEnd().suppress()
    sq_SOL = pp.AtLineStart(pp.Literal('[')).suppress()
    sq_EOL = pp.Literal(']').suppress() + eol
    ds_SOL = pp.AtLineStart(pp.Literal('["')).suppress()
    ds_EOL = pp.Literal('"]').suppress() + eol
    op_sep = pp.Literal(';').suppress()
    empty_def = pp.Empty().set_parse_action(lambda _: [[]])

    import_cmd = (pp.Keyword("import") |
                  pp.Keyword("from")) + pp.SkipTo(sq_EOL)

    signature = pp.SkipTo(sq_EOL | op_sep)

    py_sig = wrap_tag(signature, Statements.SIG)
    import_line = sq_SOL + wrap_tag(import_cmd, Statements.IMPORT) + sq_EOL

    options = pp.Group(pp.DelimitedList(pp.common.identifier()))

    sig_op_line = (
        (sq_SOL + py_sig + op_sep + options + sq_EOL) |
        (sq_SOL + py_sig + empty_def + sq_EOL)
    )

    lines = pp.OneOrMore(pp.SkipTo(pp.LineEnd()) + eol, stopOn=sq_SOL)

    text_block = ~sq_SOL + lines | pp.Empty()
    doc_string = ds_SOL + pp.SkipTo(ds_EOL) + ds_EOL

    block = pp.Group(sig_op_line) + pp.Optional(doc_string) + text_block

    full_grammar = pp.ZeroOrMore(import_line) + pp.OneOrMore(block)

    @doc_string.set_parse_action
    def _(s: str, loc: int, tokens: pp.ParseResults):
        return [(pp.lineno(loc, s), tokens[0])]

    @text_block.set_parse_action
    def _(s: str, loc: int, tokens: pp.ParseResults):
        return [(pp.lineno(loc, s), "\n".join(tokens))]

    # Command tuple are of the form:
    #      (statement, template-string, doc-string, options)
    # with the first three being tuples : (lineno, string)
    @import_line.set_parse_action
    def extract_import(_s: str, _loc: int, tokens: pp.ParseResults):
        return [(tokens[0], (0, ''), (0, ''), [])]

    @block.set_parse_action
    def extract_block(_s: str, _loc: int, t: pp.ParseResults):
        """Flatten tree into a command tuple"""
        match t:
            case [[sig, opts], tmpl]:
                return [(sig, tmpl, (0, ''), opts)]
            case [[sig, opts], docs, tmpl]:
                return [(sig, tmpl, docs, opts)]
            case _:
                raise ValueError(f"Ill-formed Block with {t[0]=}")

    return full_grammar


fTmplGrammar = get_ftmplgrammar()


def parse_file(fd):
    """Entry point to parse a .ftmpl module file."""
    return fTmplGrammar.parse_file(fd, parseAll=True)


# Code building section
def mk_function(statement: (int, int, str),
                tmpl: (int, str),
                doc: (int, str),
                options: list
                ):
    """Build AST for a block or statment. (Needs much work)"""

    # global debugHook

    sid, lineSig, strSig = statement
    _lineTmpl, strTmpl = tmpl
    _lineDoc, strDoc = doc

    match sid:
        case Statements.IMPORT:
            line = ast.parse(strSig).body[0]
            ast.fix_missing_locations(line)
            ast.increment_lineno(line, n=lineSig - 1)
            return line
        case Statements.SIG:
            for opt in options:
                if opt not in _STATE.transforms:
                    raise KeyError(f"Unknown transform option {opt}")
                (strTmpl, strDoc) = _STATE.transforms[opt](strTmpl, strDoc)

            func_def = ast.parse(f'def {strSig}:\n ...').body[0]
            doc_str = ast.parse(f'r"""{strDoc}"""').body[0]
            tmpl_strv = ast.parse(f'rf"""{strTmpl}"""').body[0].value

            func_def.body = []

            if not strDoc == '':
                func_def.body.append(doc_str)

            if not _STATE.debug_hook:
                return_ast = ast.Return(value=tmpl_strv)
                func_def.body.append(return_ast)
            else:
                _TMP_ID = "xxTemporyStringVar"
                func_def.body.append(
                    ast.Assign(targets=[ast.Name(id=_TMP_ID, ctx=ast.Store())],
                               value=tmpl_strv))

                debug = ast.parse(
                    f'__import__("{__name__}").debug_hook()').body[0]
                debug.value.args = [
                    ast.Constant(value=func_def.name),
                    ast.Name(id=_TMP_ID, ctx=ast.Load())
                ]
                debug.value.keywords = [
                    ast.keyword(
                        arg=z.arg,
                        value=ast.Name(id=z.arg, ctx=ast.Load())
                    )
                    for z in func_def.args.args
                ]
                func_def.body.append(debug)

                func_def.body.append(
                    ast.Return(value=ast.Name(id=_TMP_ID, ctx=ast.Load()))
                )

            ast.fix_missing_locations(func_def)
            ast.increment_lineno(func_def, n=lineSig - 1)
            return func_def
        case _:
            raise ValueError(f"{sid=}")  # should do better


def assemble(cst: list[(int, str, str)]):
    """Transform and build tree ready for compiling"""
    funcs = [mk_function(*args) for args in cst]

    mod = ast.Module(body=funcs, type_ignores=[])
    ast.fix_missing_locations(mod)

    return mod


# Utilities section
def loadm(modname: str):
    """Wrapper for importlib.import_module()"""
    return importlib.import_module(modname, package=None)


def unparse(fd):
    """
    Returns the equivalent Python source code for tmplfile by unparsing
    the generated AST without importing the module.
    """
    return ast.unparse(assemble(parse_file(fd)))


def set_debug_hook(callback: Callable | None) -> None:
    """
    Enable debugging and set the function to call when a template is used.
    This only has an effect on the templates are imported after it is called.
    """
    _STATE.debug_hook = callback


def debug_hook(name: str, result: str, **kwargs) -> None:
    """Invoke the registered debug hook if one is set."""
    hook = _STATE.debug_hook
    if hook:
        hook(name, result, **kwargs)


# Import and module machinery section.
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


sys.meta_path.append(fTemplateFinder())


# Test section
def tests():
    """
    I should put some tests here.
    """
    raise NotImplementedError("No tests yet.")


if __name__ == "__main__":
    tests()
