# fTemplateModules
Magically Python importable f-string template files.

## Description
This is a lightweight module that adds import hooks and parsing
logic to allow a template file containing various named f-strings
to be imported directly. Most of the hard work is done by the
Python compiler, so most syntax and error checking is exactly as 
it would be in an ordinary Python file.

## Why?
I like f-strings. A lot. However, when the strings get larger, some issues
start to arise:
1.  Long LLM prompts, and LaTeX templates are mostly human language things,
    not Python. I would like my IDE to do human language things, like
    spelling or grammar checking, for human text, and python code suggestions
    for the Python. Not the other way around.
2.  f-strings are awesome, but sometimes, especially with LaTeX, the braces `{}`
    really need to be a different character. LaTeX uses braces a lot and
    constantly escaping them is annoying.
3.  Comments that may only be relevant to the template have to be moved out
    of the string or are passed on to the output to be ignored there.
4.  Whitespace has to be pre-normalized in the string or the string has to
    be passed to a runtime function that understands not to touch f-strings 
    while normalizing.

So fTemplateModules parses and transforms a `.ftmpl` file to address these
things while cheating by passing most of the hard work back to the Python
compiler, and presenting the result as a Python module from the outside.

## Grammar
The `.ftmpl` files have a fairly simple structure: Everything is free-form
text except for a few statements which are always a complete line starting and
ending in square braces: `[some statement or command]`, which we'll call
square-lines.

In its simplest form, the file is a series of blocks where the first line is
a square-line declaring a function signature and is followed by a free-form
text block that continues to the end of the file or the next square-line:
```text
[my_llm_promptA(s: str) -> str]
My LLM Prompt with an f-string formatting : {s}

[my_llm_promptB(x: float)-> str]
Some other prompt with a {x:.2f} number.
```

More completely: the file starts with one or more import square lines 
( `[import other_module]` ), which are ordinary Python import lines wrapped
in square brackets. They're followed by one or more blocks of the form :
`[function-signature ; optional-comma-seperated-options]` followed by 
an optional square-line for a doc-string description, which is followed
by the associated free-form text. The doc-string square-line uses an
additional quote: `["A free-form text description"]` (see example below).
If a `;` and comma separated list of optional transforms is given, these
transforms are applied to the (template-string, doc-string) pair for that
block in the order given in the list. 

So for example :
```text
[test_prompt_tex(sub: int) -> str ; remove_cpp_comments, latex_tmpl]
["A LaTeX test template"]
A string with some math in it $x=<sub>$ $\vec{x}=\mathbf{<sub>}$
and a c++ like comment removed /* comment */ something something
// Another c comemnt
```

As with any mixed-language parser, there are some edge cases. Square
braces `[]` were picked because they're not often used in human text and
don't clash with f-strings `{}`. The ';' was picked as an option seperator
because Python rarely uses it, and it means line-break anyway. Lastly,
`"]` at the end of a line ends a doc-string, so don't do that if you
don't want it to end.

Each block is rearranged into a single function. The above example becomes:
```python
def test_prompt_tex(sub: int) -> str:
    """A LaTeX test template"""
    return f'A string with some math in it $x={sub}$ $\\vec{{x}}=\\mathbf{{{sub}}}$\nand a c++ like comment removed  thing\n\n'
```
and is  made available for import in the normal way.

You can import other modules using an `[import line]` at the
beginning of the file. This can be any valid module, either another
`.ftmpl` file or an ordinary Python module. One of the examples uses
this to import the `json.dumps()` function.

Once imported, everything should work as expected for any Python module,
including the `help()` function and, with a little hacking, `pydoc()` (see
the pydocftmpl.py example)

## Transforms
Current built-in transforms are :

| Option | Description |
| :--:|:--- |
| remove_cpp_comments    | Use PyParsing's `cpp_style_comment()` to remove c++ style comments.        |
| remove_python_comments | Use PyParsing's `python_style_comment()` to remove python style comments.  |
| remove_html_comments   | Use PyParsing's `html_comment()` to remove html style comments.            |
| append_doc             | Append the current template string to the current doc string.            |
| unwrap_lines           | Unwrap line-broken lines and normalize line white space. This transform  |
|                        | reduces the number of EOLs in a row and replaces an EOL with a space if  |
|                        | it is the only one. |
| latex_tmpl             | Transform for LaTeX templates: escape `{}` to `{{}}` and 
|                        | map `<>` to `{}` |

## Custom Transforms
Each transform is a function with signature `(str, str) -> (str, str)`, and is
added to the possible options list with the `@add_transform(NAME)` decorator:

```python
@add_transform("transform_name")
def _(tmpl: str, docs: str) -> (str, str):
    ...
    return (tmpl, docs)
```
See the source code for some examples.

## Example Templates
(ToDo: better examples! A longer example is in the example directory)

The following Python :
```python
import ftemplatemodules
from prompts import test_prompt

print(test_prompt(
    data={"key1": "something-one", "key2": "something-two"},
    action="Say Hello!"
))
```
uses `prompts.ftmpl` :
```text
[from basePrompts import *]
[from json import dumps]

[test_prompt(data, action) -> str]
["Prompt template function for a friendly LLM"]
You are a friendly LLM.

{action}

The JSON is {dumps(data)}

{jsonInstructions()}
```
and `basePrompts.ftmpl`:
```text
[jsonInstructions() -> str]
Output as well-formed JSON, where the JSON is complete, should avoid using dictionaries, and has a line length of 70 characters.
````
to produce :
```text
You are a friendly LLM.

Say Hello!

The JSON is {"key1": "something-one", "key2": "something-two"}

Output as well formed JSON, where the JSON is complete, should avoid using dictionaries, and has a line length of 70 characters.
```

# ToDo
1. Better examples.
2. Some proper tests.
3. The constructed functions are parsed literally with `python
ast.parse(f'def {strSig}:\n return f"""{strTmp}"""') `.
This causes the column numbering to be off in error messages. I
need to split it into several `parse()` calls to control the line and
column numbering better.

