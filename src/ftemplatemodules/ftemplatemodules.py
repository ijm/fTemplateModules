import sys
import ast
import pyparsing as pp
from pathlib import Path
from importlib.machinery import ModuleSpec, SourcelessFileLoader
import importlib
# from importlib.util import spec_from_loader
# from importlib import module
from typing import Callable


# Transforms section
#
# Define optional transforms, and assemble them into a dictionary.
# This is implemented as seperate decorated functions rather than a
# dictionary of lambdas.
# The decorator takes the name of the option as seen in the template as
# it's only argument and adds the assosiated function under that name.
# transforms are always of the form (str, str)->(str, str) where the first
# string is the template string, and the second string is the doc-string

transformMap = {}
debugHook = None


def add_transform(key: str):
    """Curried decorator function to add a template to the options dictionary"""
    def f(func: Callable[[str, str], [str, str]]):
        transformMap[key] = func
    return f


@add_transform("remove_cpp_comments")
def _(tmpl: str, docs: str) -> (str, str):
    """Use PyParsing's cpp_style_comment() to remove c++ style comments"""
    return (pp.cpp_style_comment().suppress().transformString(tmpl), docs)


@add_transform("remove_python_comments")
def _(tmpl: str, docs: str) -> (str, str):
    """Use PyParsing's python_style_comment() to remove python style comments"""
    return (pp.python_style_comment().suppress().transformString(tmpl), docs)


@add_transform("remove_html_comments")
def _(tmpl: str, docs: str) -> (str, str):
    """Use PyParsing's html_comment() to remove html style comments"""
    return (pp.html_comment().suppress().transformString(tmpl), docs)


@add_transform("append_doc")
def _(tmpl: str, docs: str) -> (str, str):
    """Append the current template string to the current doc string."""
    return (tmpl, docs + tmpl)


@add_transform("unwrap_lines")
def _(tmpl: str, docs: str) -> (str, str):
    """
    Unwrap line-broken lines and normalize line white space.
    This transform reduces the number of EOLs in a row and replaces
    an EOL with a space if it is the only one.
    """
    @pp.OneOrMore(pp.lineEnd()).set_parse_action
    def newlines(s: str, lk: int, t: pp.ParseResults):
        return [" "] if len(t) == 1 else t[1:]

    return (newlines.transformString(tmpl), docs)


@add_transform("latex_tmpl")
def _(tmpl: str, docs: str) -> (str, str):
    """Transform for Latex Templates to escape {} to {{}} and map <> to {}"""

    def replace(elem, target: str):
        @elem.set_parse_action
        def _(s: str, lk: int, t: pp.ParseResults):
            return [target]
        return elem

    transform = replace(pp.Char("{"), "{{") |\
        replace(pp.Char("}"), "}}") |\
        replace(pp.Char("<"), "{") |\
        replace(pp.Char(">"), "}")

    return (transform.transformString(tmpl), docs)


# Parser section.
class Statements:
    IMPORT = 1
    SIG = 2


def get_ftmplgrammar():
    def wrapTag(elem, tag: int):
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

    import_cmd = (pp.Keyword("import") | pp.Keyword("from")) + pp.SkipTo(sq_EOL)

    signature = pp.SkipTo(sq_EOL | op_sep)

    py_sig = wrapTag(signature, Statements.SIG)
    import_line = sq_SOL + wrapTag(import_cmd, Statements.IMPORT) + sq_EOL

    options = pp.Group(pp.DelimitedList(pp.common.identifier()))

    sig_op_line =\
        (sq_SOL + py_sig + op_sep + options + sq_EOL) |\
        (sq_SOL + py_sig + empty_def + sq_EOL)

    lines = pp.OneOrMore(pp.SkipTo(pp.LineEnd()) + eol, stopOn=sq_SOL)

    text_block = ~sq_SOL + lines | pp.Empty()
    doc_string = ds_SOL + pp.SkipTo(ds_EOL) + ds_EOL

    block = pp.Group(sig_op_line) + pp.Optional(doc_string) + text_block

    all = pp.ZeroOrMore(import_line) + pp.OneOrMore(block)

    @doc_string.set_parse_action
    def _(s: str, lk: int, t: pp.ParseResults):
        return [(pp.lineno(lk, s), t[0])]

    @text_block.set_parse_action
    def _(s: str, lk: int, t: pp.ParseResults):
        return [(pp.lineno(lk, s), "\n".join(t))]

    # Command tuple are of the form:
    #      (statement, template-string, doc-string, options)
    # with the first three being tuples : (lineno, string)
    @import_line.set_parse_action
    def _(s: str, lk: int, t: pp.ParseResults):
        return [(t[0], (0, ''), (0, ''), [])]

    @block.set_parse_action
    def _(s: str, lk: int, t: pp.ParseResults):
        """Flatten tree into a command typle"""
        match t:
            case [[sig, opts], tmpl]:
                return [(sig, tmpl, (0, ''), opts)]
            case [[sig, opts], docs, tmpl]:
                return [(sig, tmpl, docs, opts)]
            case _:
                raise ValueError(f"Illformed Block with {t[0]=}")

    return all


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

    global debugHook

    id, lineSig, strSig = statement
    lineTmpl, strTmpl = tmpl
    lineDoc, strDoc = doc

    if id == Statements.IMPORT:
        line = ast.parse(strSig).body[0]
        ast.fix_missing_locations(line)
        ast.increment_lineno(line, n=lineSig - 1)
        return line
    elif id == Statements.SIG:
        for opt in options:
            if opt not in transformMap:
                raise KeyError(f"Unknown transform option {opt}")
            (strTmpl, strDoc) = transformMap[opt](strTmpl, strDoc)

        func_def = ast.parse(f'def {strSig}:\n ...').body[0]
        doc_str = ast.parse(f'r"""{strDoc}"""').body[0]
        tmpl_strv = ast.parse(f'rf"""{strTmpl}"""').body[0].value

        func_def.body = []

        if not strDoc == '':
            func_def.body.append(doc_str)

        if not debugHook:
            return_ast = ast.Return(value=tmpl_strv)
            func_def.body.append(return_ast)
        else:
            TMP_ID = "xxTemporyStringVar"
            func_def.body.append(
                ast.Assign(targets=[ast.Name(id=TMP_ID, ctx=ast.Store())],
                           value=tmpl_strv))

            debug = ast.parse(f'__import__("{__name__}").debug_hook()').body[0]
            debug.value.args = [
                ast.Constant(value=func_def.name),
                ast.Name(id=TMP_ID, ctx=ast.Load())
            ]
            debug.value.keywords = [
                ast.keyword(arg=z.arg, value=ast.Name(id=z.arg, ctx=ast.Load()))
                for z in func_def.args.args
            ]
            func_def.body.append(debug)

            func_def.body.append(
                ast.Return(value=ast.Name(id=TMP_ID, ctx=ast.Load()))
            )

        ast.fix_missing_locations(func_def)
        ast.increment_lineno(func_def, n=lineSig - 1)
        return func_def

        # line = ast.parse(f'def {strSig}:\n return rf"""{strTmpl}"""').body[0]
        # or
        # line = ast.parse(f'def {strSig}:\n """{strDoc}"""\n return rf"""{strTmpl}"""').body[0]
    else:
        raise ValueError(f"{id=}")  # should do better


def assemble(cst: list[(int, str, str)]):
    """Transform and build tree ready for compiling"""
    funcs = [mk_function(*args) for args in cst]

    mod = ast.Module(body=funcs, type_ignores=[])
    ast.fix_missing_locations(mod)

    return mod


# Utilities section
def loadm(modname: str):
    """Wrapper for importlibe.import_module()"""
    return importlib.import_module(modname, package=None)


def unparse(fd):
    """
    Returns the equivilant Python source code for tmplfile by unparseing
    the generated AST without importing the module.
    """
    return ast.unparse(assemble(parse_file(fd)))


def set_debug_hook(callback: Callable | None) -> None:
    """
    Enable debugging and set the function to call when a template is used.
    This only has an effect on the templates are imported after it is called.
    """
    global debugHook
    debugHook = callback


def debug_hook(name: str, result: str, **kargs) -> None:
    if debugHook:
        debugHook(name, result, **kargs)


# Import and module machinery section.
class fTemplateLoader(SourcelessFileLoader):
    SUFFIX = ".ftmpl"

    def __init__(self, name, path):
        super().__init__(name, path)

    def is_package(self, ame):
        return False

    def get_code(self, name):
        """Load and compile the module code"""

        path = Path(name).with_suffix(self.SUFFIX)

        with open(path, "rt") as fd:
            cst = parse_file(fd)

        return compile(assemble(cst), path.resolve(), 'exec')


class fTemplateFinder(object):
    def find_spec(self, name: str, path: str, target) -> ModuleSpec:
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


