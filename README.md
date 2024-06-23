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

In it's simplist form the file is a series of blocks where the first line is
a square-line declaring a function signature and is followed by a free-form
text block that continues to the end of file or the next square-line:
```text
[my_llm_promptA(s: str) -> str]
My LLM Promp with an f-string formating : {s}

[my_llm_promptB(x: float)-> str]
Some other prompt with a {x:.2f} number.
```

More completely: the file starts with one or more import square lines 
( `[import other_module]` ), which are ordinary Python import lines wrapped
in square brackets. They're followed by one or more blocks of the form :
`[function-signature ; optional-comma-seperated-options]` followed by 
an optional square-line for a doc-string description, which is followed
by the associated free-form text. The doc-string square-line uses an
additional quote: `["A defreeform text description"]` (see example below).
If a `;` and comma seperated list of optional transforms is given, these
transforms are applied to the (template-string, doc-string) pair for that
block n the order given in the list.

As with any mixed-language parser there are some edge cases. Square
braces `[]` were picked because they're not often used in human text and
don't clash with f-srings `{}`. The ';' was picked as an option seperator
because Python rarely uses it, and it means line-break anyway. Lastly
`"]` at the end of a line ends a doc-string so don't do that if you
don't want it to end.

Each block is rearranged into the code :
```python
def function(signature):
    """Description text"""
    return f"""Free form text in f-string syntax"""
```
and made available for import in the normal way.
You can also import other modules using an `[import line]` at the
beginning of the file. This can be any valid module, so this example
shows both an ordinary Python import and another `.ftmpl` file:

Once imported everything should work as expected for any python module,
including the `help()` function and, with a little hacking `pydoc()`

## Example
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

