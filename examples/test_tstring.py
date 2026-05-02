import ftemplatemodules.auto  # noqa: F401 # pylint: disable=unused-import
from prompts_t import test_prompt_t  # noqa # pylint: disable=import-error

# Python 3.14+ only - requires t-string support
from string.templatelib import Interpolation


def render(tmpl):
    return "".join(
        format(p.value, p.format_spec)
        if isinstance(p, Interpolation) else p
        for p in tmpl
    )


def test_t():
    template = test_prompt_t(
        data={"key1": "something-one", "key2": "something-two"},
        action="Say Hello!"
    )
    print(render(template))


if __name__ == "__main__":
    test_t()
