import sys
import ast
import pyparsing as pp
from pathlib import Path
from importlib.machinery import ModuleSpec, SourcelessFileLoader
from importlib.util import spec_from_loader


modulesuffix = ".ftmpl"
boolParseOptions = ["cstylecomments", "unwraplines", "appendtodoc"]


class Statements:
    IMP = 1
    SIG = 2


def get_ftmplgrammar():
    def wrapTag(elem, tag):
        def h(s: str, lk: int, t: pp.ParseResults):
            return [(tag, pp.lineno(lk, s), " ".join(t))]
        return elem.set_parse_action(h)

    def raise_error(s, loc, toks):
        raise pp.ParseFatalException(s, loc, "Unknown Option")

    eol = pp.LineEnd().suppress()
    sq_SOL = pp.AtLineStart(pp.Literal('[')).suppress()
    sq_EOL = pp.Literal(']').suppress() + eol
    ds_SOL = pp.AtLineStart(pp.Literal('["')).suppress()
    ds_EOL = pp.Literal('"]').suppress() + eol
    op_sep = pp.Literal(';').suppress()
    empty_def = pp.Empty().set_parse_action(lambda x: [[]])

    import_cmd = (pp.Keyword("import") | pp.Keyword("from")) + pp.SkipTo(sq_EOL)

    signature = pp.SkipTo(sq_EOL | op_sep)

    py_sig = wrapTag(signature, Statements.SIG)
    import_line = sq_SOL + wrapTag(import_cmd, Statements.IMP) + sq_EOL
    # options = pp.oneOf(pp.Literal(op) for op in boolOptions)
    opts = pp.oneOf(boolParseOptions, as_keyword=True) |\
        pp.SkipTo(pp.White() | sq_EOL).set_parse_action(raise_error)

    sig_op_line =\
        (sq_SOL + py_sig + op_sep + pp.Group(pp.DelimitedList(opts)) + sq_EOL) |\
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
        match t:
            case [[sig, opts], tmpl]:
                return [(sig, tmpl, (0, ''), opts)]
            case [[sig, opts], docs, tmpl]:
                return [(sig, tmpl, docs, opts)]
            case _:
                raise ValueError(f"Illformed Block with {t[0]=}")

    return all


fTmplGrammar = get_ftmplgrammar()


def parse(path):
    """Entry point to parse a .ftmpl module file."""

    with path.open("rt") as fd:
        parseTree = fTmplGrammar.parseFile(fd, parseAll=True)

    return parseTree


def mk_function(statement: (int, int, str),
                tmpl: (int, str),
                doc: (int, str),
                options: list
                ):
    """Build AST for a block or statment. (Needs much work)"""
    id, lineSig, strSig = statement
    lineTmpl, strTmp = tmpl
    lineDoc, strDoc = doc

    if id == Statements.IMP:
        line = ast.parse(strSig).body[0]
    elif id == Statements.SIG:
        if strDoc == '':
            line = ast.parse(f'def {strSig}:\n return f"""{strTmp}"""').body[0]
        else:
            line = ast.parse(f'def {strSig}:\n """{strDoc}"""\n return f"""{strTmp}"""').body[0]
    else:
        raise ValueError(f"{id=}")  # should do better

    ast.increment_lineno(line, n=lineSig - 1)
    ast.fix_missing_locations(line)

    return line


def assemble(cst: list[(int, str, str)]):
    funcs = [mk_function(*args) for args in cst]

    mod = ast.Module(body=funcs, type_ignores=[])
    ast.fix_missing_locations(mod)

    return mod


class fTemplateLoader(SourcelessFileLoader):
    def __init__(self, name, path):
        super().__init__(name, path)

    def is_package(self, ame):
        return False

    def get_code(self, name):
        """Load and compile the module code"""

        path = Path(name).with_suffix(modulesuffix)
        cst = parse(path)
        mod = assemble(cst)
        obj = compile(mod, path.resolve(), 'exec')
        return obj


class fTemplateFinder(object):
    def find_spec(self, name: str, path: str, target) -> ModuleSpec:
        """Look for a toplevel file with ending in `modulesuffix` (.ftmpl)"""

        if Path(name).with_suffix(modulesuffix).is_file():
            return spec_from_loader(name, fTemplateLoader(name, path))
        return None


sys.meta_path.append(fTemplateFinder())


def tests():
    """
    I should put some tests here.
    """
    raise NotImplementedError("No tests yet.")


if __name__ == "__main__":
    tests()


