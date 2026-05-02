"""Code generation: AST building and compilation utilities."""

import ast
import importlib
from typing import Callable

# Import registry first
from .registry import _STATE

# Import transforms and parsers for side-effect registration
# (modules register themselves via decorators on import)
from . import transforms  # noqa: F401
from . import parsers  # noqa: F401

# Import grammar
from .grammar import parse_file, Statements


def mk_function(statement: (int, int, str),
                tmpl: (int, str),
                doc: (int, str),
                options: list
                ):
    """Build AST for a block or statment. (Needs much work)"""

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

            # Determine return type and select appropriate parser
            if func_def.returns and isinstance(func_def.returns, ast.Name):
                ret_type = func_def.returns.id
            else:
                ret_type = "str"

            if ret_type not in _STATE.parsers:
                raise KeyError(
                    f"No parser registered for return type: {ret_type}")

            tmpl_strv = _STATE.parsers[ret_type](strTmpl)

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

                # Use hardcoded package name for the import hook generated code
                debug = ast.parse(
                    '__import__("ftemplatemodules").debug_hook()').body[0]
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
