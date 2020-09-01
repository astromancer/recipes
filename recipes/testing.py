import inspect
import textwrap
from collections import defaultdict

import pytest

class Expect(object):
    """
    Testing helper for testing expected return values for functions.
    
    For example, to test that the function `decimal` returns the expected
    values, do the following:
    >>> ex = Expect(decimal)
    >>> ex.expects({ex.decimal(1e4):            '10000.0',
    ...             ex.decimal(0.0000123444):   '0.0000123'},
    ...             globals())

    This will automatically construct a test: 'test_dicimal' which has the same
    signature as the function `decimal`. The the sequence of input output pairs
    passed to the `expects` method is used to parametrize the test, so that
    pytet will include all cases in your test run
    """
    def __init__(self, *funcs):
        self.cache = {}
        for f in funcs:
            self.cache[f] = inspect.signature(f)
            setattr(self, f.__name__, self.make_args(f))

    # def __getitem__(self, func):
    #     return self.make_args(func)

    def make_args(self, func):
        def wrapped(*args, **kws):
            ba = self.cache[func].bind(*args, **kws)
            ba.apply_defaults()
            return func, tuple(ba.arguments.items())
        return wrapped

    def get_names_values(self, spec): 
        values = defaultdict(list)
        expected = []
        for items, answer in spec.items():
            func, items = items
            for name, val in items:
                values[name].append(val)
            expected.append(answer)
        names = tuple(values.keys()) + ('output', )
        values = zip(*values.values(), expected)
        return func, names, values

    def make_test(self, func):
        args = ", ".join(self.cache[func].parameters.keys())
        name = func.__name__
        test_name = f'test_{name}'
        code = textwrap.dedent(
            f'''
            global {test_name}
            def {test_name}({args}, output):
                assert {name}({args}) == output
            ''')
        return test_name, code

    def expects(self, spec, god):
        func, names, values = self.get_names_values(spec)
        assert func.__name__ not in globals()

        test_name, code = self.make_test(func)
        locals_ = {}
        exec(code, god, locals_)
        # print(locals_, test_name, god) # (locals_[test_name])
        return pytest.mark.parametrize(names, values)(god[test_name])

