# std
import sys
from concurrent.futures import ThreadPoolExecutor

# third-party
import pytest
from loguru import logger

# local
from recipes.oo.property import ClassProperty, CachedProperty


# ---------------------------------------------------------------------------- #


@pytest.fixture
def fast_thread_switching():
    """
    Fixture that reduces thread switching interval.
    This makes it easier to provoke race conditions.
    """
    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    yield
    sys.setswitchinterval(old)


# ---------------------------------------------------------------------------- #


class _TestClassProperty:
    _name = None
    """Optional `name` attribute. Defaults to class' `__name__` if not
    over-written by inheritors."""

    @ClassProperty
    @classmethod
    def name(cls):
        return cls._name or cls.__name__

    @name.setter
    def name(cls, name):
        cls.set_name(name)

    @classmethod
    def set_name(cls, name):
        assert isinstance(name, str)
        cls._name = name


def test_classproperty():
    case = _TestClassProperty()
    assert case.name == 'Foo'

    case.name = 'Yo'
    assert case.name is _TestClassProperty.name
    # ('Yo', 'Yo')
    _TestClassProperty.name = 'zzz'
    assert case.name is _TestClassProperty.name is _TestClassProperty._name
    # ('zzz', 'zzz')

# ---------------------------------------------------------------------------- #


class _TestCaseCacheProperty:
    def __init__(self):
        self._count = 0

    @CachedProperty
    def count(self):
        logger.debug('Incrementing count')
        self._count += 1
        logger.debug('_count = {}',  self._count)
        return self._count

    @count.deleter
    def count(self):
        self._count = 0
        logger.debug('Count reset to {}',  self._count)

    @CachedProperty(read_only=True)
    def read_only(self):
        pass

    @CachedProperty(depends_on=count)
    def neg_count(self):
        return -self.count

    @CachedProperty(depends_on=neg_count)
    def imaginary_neg_count(self):
        return 1j * self.neg_count

    @CachedProperty
    def letter(self):
        return 'a'

    @CachedProperty(depends_on=(count, letter))
    def multiple_dependencies(self):
        return self.count, self.letter

    multiple_dependencies_setter_ran = False

    @multiple_dependencies.setter
    def multiple_dependencies(self, val):
        self.multiple_dependencies_setter_ran = True
        self.count, self.letter = val


# lazyprop_test_case = _TestCaseCacheProperty()

class TestCachedProperty:
    @pytest.fixture()
    def case(self):
        return _TestCaseCacheProperty()

    def test_basic(self, case):
        for _ in range(10):
            case.count

        assert case.count == 1

    def test_assign(self, case):
        # test assignment
        case.count = 2
        case.count
        assert case.count == 2

    def test_delete(self, case):
        # test assignment
        case.count = 7

        del case.count
        assert case.count == 1

    def test_readonly(self, case):
        with pytest.raises(AttributeError):
            case.read_only = 1

    def test_readonly_setter(self):
        with pytest.raises(AttributeError):
            class _TestCaseCacheProperty:
                @CachedProperty(read_only=True)
                def read_only(self):
                    pass

                @read_only.setter
                def read_only(self, _):
                    pass

    def test_dependency_type(self):
        with pytest.raises(TypeError):
            class _TestCaseCacheProperty:
                @property
                def a(self):
                    pass

                @CachedProperty(depends_on=a)
                def b(self):
                    pass

    def test_dependency(self, case):
        # test basic
        case.count
        assert case.neg_count == -1

        # test derived update
        case.count = 2
        assert case.neg_count == -2

        # test delete parent deletes child
        del case.count
        assert case.neg_count == -1

        # test assign
        case.neg_count = 2
        assert case.neg_count == 2

        # test delete child
        del case.neg_count
        assert case.neg_count == -1

    def test_grandparent_dependency(self, case):
        # test basic
        case.neg_count
        assert case.imaginary_neg_count == -1j

        # test derived update
        case.neg_count = -2
        assert case.imaginary_neg_count == -2j

        # test delete parent deletes child
        del case.neg_count
        assert case.imaginary_neg_count == -1j

        # test assign
        case.imaginary_neg_count = 2
        assert case.imaginary_neg_count == 2

        # test delete child
        del case.imaginary_neg_count
        assert case.imaginary_neg_count == -1j

    def test_multiple_dependencies(self, case):

        assert case.multiple_dependencies == (1, 'a')

        # edit parent
        case.count = 0
        assert case.multiple_dependencies == (0, 'a')

        case.letter = 'z'
        assert case.multiple_dependencies == (0, 'z')

        del case.count, case.letter
        assert case.multiple_dependencies == (1, 'a')

        case.multiple_dependencies = (7, 'z')
        assert case.multiple_dependencies_setter_ran
        assert case.count == 7
        assert case.letter == 'z'
        assert case.multiple_dependencies == (7, 'z')

    # test_threadsafe copied from astropy

    def test_threadsafe(self, fast_thread_switching):
        """
        Test thread safety of CachedProperty.
        """

        # This test is generally similar to test_classproperty_lazy_threadsafe
        # above. See there for comments.

        class A:
            def __init__(self):
                self.calls = 0

            @CachedProperty
            def foo(self):
                self.calls += 1
                return object()

        workers = 8
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for p in range(10000):
                a = A()
                futures = [executor.submit(lambda: a.foo) for i in range(workers)]
                values = [future.result() for future in futures]
                assert a.calls == 1
                assert a.foo is not None
                assert values == [a.foo] * workers

