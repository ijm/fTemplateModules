# fTemplateModules
Magically Python importable f-string template files.

## Description
This is a lightweight module that adds import hooks and parsing
logic to allow a template file containing various named f-strings
to be imported directly. Most of the hard work is done by the
Python compiler, so most syntax and error checking is exactly as 
it would be in an ordinary python file.

The .ftmpl files have a simple structure, they are repeated blocks
of the form :

```
[python-function(signature)]
Free form text in f-string syntax
```
Each block is rearranged into the code :
```python
def function(signature):
    return f"""Free form text in f-string syntax"""
```
and made available for import in the normal way.
You can also import other modules using an `[import line]` at the
beginning of the file. This can be any valid module, so this example
shows both an ordinary Python import and another .ftmpl file:

## Example
(ToDo: better examples!)

The following python :
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
2. The constructed functions are parsed literally with `python
ast.parse(f'def {strSig}:\n return f"""{strTmp}"""') `.
This causes the column numbering to be off in error messages. I
need to split it into several `parse()` calls to control the line and
column numbering better.
3. I could add a translation step before parsing to do two things:
remove comments of a specified type if the user wants them, and to
change the template variable designated characters from '{}', which
would be most useful for LaTeX templates.

