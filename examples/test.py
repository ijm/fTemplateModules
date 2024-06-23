import ftemplatemodules
from prompts import test_prompt, test_prompt_tex, testB

print(f"{test_prompt.__doc__=}")
print(test_prompt(
    data={"key1": "something-one", "key2": "something-two"},
    action="Say Hello!"
))

print(f"{test_prompt_tex.__doc__=}")
print(test_prompt_tex(42))

print(f"{testB.__doc__=}")
print(testB())

