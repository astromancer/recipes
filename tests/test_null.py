from recipes.oo import Null


class TestNull:
    def test_init(self):
        # constructing
        n = Null()
        n = Null('value')
        n = Null('value', param='value')

    def test_call(self):
        #  calling
        n = Null()
        n()
        n('value')
        n('value', param='value')

    def test_attrs(self):
        # attribute handling
        n = Null()
        n.attr1
        n.attr1.attr2
        n.method1()
        n.method1().method2()
        n.method('value')
        n.method(param='value')
        n.method('value', param='value')
        n.attr1.method1()
        n.method1().attr1

        n.attr1 = 'value'
        n.attr1.attr2 = 'value'

        del n.attr1
        del n.attr1.attr2.attr3

    def test_repr(self):
        # representation and conversion to a string

        assert repr(n) == '<Null>'
        assert str(n) == 'Null'
