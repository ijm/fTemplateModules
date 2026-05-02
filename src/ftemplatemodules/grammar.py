"""Grammar definition for .ftmpl files."""

import pyparsing as pp


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
