import sys
import pyparsing as pp
import ast
from pathlib import Path
from importlib.machinery import ModuleSpec, SourcelessFileLoader
from importlib.util import spec_from_loader


modulesuffix = ".ftmpl"


class statements():
    imp = 1
    sig = 2


def getFTmplGrammar():
    def wrapBlk(elem):
        """
        Rejoin lines together, recording the lineno of the start.
        """
        def g(s: str, lk: int, t: pp.ParseResults):
            return [(pp.lineno(lk, s), "\n".join(t))]
        return elem.set_parse_action(g)

    def wrapTag(elem, tag):
        def h(s: str, lk: int, t: pp.ParseResults):
            return [(tag, pp.lineno(lk, s), " ".join(t))]
        return elem.set_parse_action(h)

    eol = pp.LineEnd().suppress()

    importCmd = (pp.Literal("import") | pp.Literal("from")) +\
        pp.SkipTo(']' + eol)

    signature = pp.SkipTo("]" + eol)

    pythonCode = wrapTag(importCmd, statements.imp) |\
        wrapTag(signature, statements.sig)

    pythonBlock = pp.AtLineStart("[").suppress() + pythonCode +\
        pp.Literal("]").suppress() + eol

    textBlock = ~pp.Literal("[") +\
        pp.OneOrMore(pp.SkipTo(pp.LineEnd()) + eol,
                     stopOn=pp.AtLineStart("[")
                     ) | pp.Empty()

    block = pythonBlock + wrapBlk(textBlock)

    all = pp.OneOrMore(block)

    @block.set_parse_action
    def g(s: str, lk: int, t: pp.ParseResults):
        return [(t[0], t[1])]

    return all


fTmplGrammar = getFTmplGrammar()


def parse(path):
    """
    Split up the template file into block of the form
      [python signature]
      Free form text.
    """

    with path.open("rt") as fd:
        parseTree = fTmplGrammar.parseFile(fd)

    return parseTree


def mkFunction(statment: (int, int, str), tmpl: (int, str)):
    id, lineSig, strSig = statment
    lineTmpl, strTmp = tmpl

    if id == statements.imp:
        line = ast.parse(strSig).body[0]
    elif id == statements.sig:
        line = ast.parse(f'def {strSig}:\n return f"""{strTmp}"""').body[0]
    else:
        raise ValueError(f"{id=}")  # should do better

    ast.increment_lineno(line, n=lineSig - 1)
    ast.fix_missing_locations(line)
    # print(ast.dump(func, include_attributes=True))
    return line


def assemble(cst: list[(int, str)]):
    funcs = [mkFunction(sig, tmpl) for sig, tmpl in cst]

    mod = ast.Module(body=funcs, type_ignores=[])
    ast.fix_missing_locations(mod)

    return mod


class fTemplateLoader(SourcelessFileLoader):
    def __init__(self, name, path):
        super().__init__(name, path)

    def is_package(self, ame):
        return False

    def get_code(self, name):
        path = Path(name).with_suffix(modulesuffix)
        cst = parse(path)
        mod = assemble(cst)
        obj = compile(mod, path.resolve(), 'exec')
        return obj


class fTemplateFinder(object):
    def find_spec(self, name: str, path: str, target) -> ModuleSpec:
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


