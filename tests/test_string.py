from recipes.string import match_brackets, Percentage
import pytest


# @pytest.mark.skip()
@pytest.mark.parametrize('s, brackets, result',
                         [('hello(world)', '()', 'world'),
                          ('unclosed((((((', '()', None),
                          ('nested((([inside]))]]])))', '[]', 'inside'),
                          ('<s>', '<>', 's'),
                          ('((())', '()', None)])
def test_match_brackets(s, brackets, result):
    r, (i, j) = match_brackets(s, brackets)
    assert r == result
    if r:
        assert r == s[i+1:j]


# @pytest.mark.skip()
@pytest.mark.parametrize('s, b, e',
                         [('foo{bla', '{}', 'bla'),
                          ('open((((((', '()', '((((('),
                          ('((())', '()', '(())')])
def test_brackets_must_close(s, b, e):
    sub, (_, j) = match_brackets(s, b, must_close=-1)
    assert sub == e
    assert j is None


@pytest.mark.parametrize('s', ['(', 'also_open((((((', '((())'])
def test_brackets_must_close_raises(s):
    with pytest.raises(ValueError):
        match_brackets(s, must_close=True)


@pytest.mark.parametrize('s, e', [('20%', 2469),
                               ('100.01%', 12346.2345),
                               ('12.0001 %', 1481.412345)])
def test_percentage(s, e):
    assert Percentage(s).of(12345.) == e
   


# @pytest.mark.parametrize('s', ['3r', 
#                                'some text 100.0.ss',
#                                '12.0001 %'])
# def test_percentage_raises(s):
#     n = Percentage(s).of(12345.)
#     print(n)
