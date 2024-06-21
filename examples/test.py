import ftemplatemodules
from prompts import test_prompt

print(test_prompt(
    data={"key1": "something-one", "key2": "something-two"},
    action="Say Hello!"
))
