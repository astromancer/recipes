
from recipes.oo.property import lazyproperty


class _TestClass:
    _computed = False

    @lazyproperty
    def p1(self):
        return 42

    @lazyproperty(depends_on=p1)
    def p2(self):
        self._computed = True
        return self.p1 * 10


def test_codelete():
    t = _TestClass()
    t.p2
    del t.p1
    t._computed = False
    t.p2
    assert t._computed


def test_delete_on_overwrite():
    t = _TestClass()
    t.p2
    t.p1 = 41
    t._computed = False
    t.p2
    assert t._computed
