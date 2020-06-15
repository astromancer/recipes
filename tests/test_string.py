from recipes.string import match_brackets, Percentage
import pytest


@pytest.mark.skip()
@pytest.mark.parametrize('s, brackets, result',
                         [('hello(world)', '()', 'world'),
                          ('unclosed((((((', '()', None),
                          ('nested((([inside]))]]])))', '[]', 'inside'),
                          ('<s>', '<>', 's')
                          ])
def test_match_brackets(s, brackets, result):
    r, (i, j) = match_brackets(s, brackets)
    assert r == result
    if r:
        assert r == s[i+1:j]


@pytest.mark.skip()
def test_match_brackets_raises():
    with pytest.raises(ValueError):
        match_brackets('unclosed((((((', must_close=True)


@pytest.mark.parametrize('s', ['3%',
                               '100.01%',
                               '12.0001 %'])
def test_percentage(s):
    n = Percentage(s).of(12345.)
    print(n)

@pytest.mark.parametrize('s', ['3',
                               'some text 100.0.ss',
                               '12.0001 %'])
def test_percentage_raises(s):
    n = Percentage(s).of(12345.)
    print(n)
