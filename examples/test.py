import ftemplatemodules
from prompts import test_prompt, test_prompt_tex, testB


def test1():
    print(f"{test_prompt.__doc__=}")
    print(test_prompt(
        data={"key1": "something-one", "key2": "something-two"},
        action="Say Hello!"
    ))


def test2():
    print(f"{test_prompt_tex.__doc__=}")
    print(test_prompt_tex(42))


def test3():
    print(f"{testB.__doc__=}")
    print(testB())


def main():
    test1()
    test2()
    test3()


if __name__ == "__main__":
    main()


