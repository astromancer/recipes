

from recipes.oo.meta import tagger
from recipes.oo.meta.tagger import MethodTaggerFactory, TagManagerBase

# ---------------------------------------------------------------------------- #

Base, method_tagger = tagger.factory('mytag')


class _TestCaseMethodTagger0(Base):
    @method_tagger('info')
    def method1(self, *args):
        return args


def test_method_tagger0():
    assert _TestCaseMethodTagger0().method1.mytag == ('info', )


# ---------------------------------------------------------------------------- #
CollectWorkers, worker = tagger.factory('_is_worker', 'workers')


class _TestCaseMethodTagger1(CollectWorkers):
    @worker(1)
    def method1(self, *args):
        return args


def test_method_tagger1():
    obj = _TestCaseMethodTagger1()
    assert obj.method1._is_worker == (1, )
    assert obj.workers == {obj.method1: (1, )}


# ---------------------------------------------------------------------------- #
alias = MethodTaggerFactory('_is_alias')


class AliasManager(TagManagerBase,
                            tag='_is_alias',
                            collection='_aliases'):

    def __init__(self):
        super().__init__()
        for method, (alias, ) in self._aliases.items():
            setattr(self, alias, method)

    @alias('alternate_name_for_method1')
    def method1(self, *args):
        return args


def test_method_tagger2():
    obj = AliasManager()
    assert (info := obj.method1._is_alias) == ('alternate_name_for_method1', )
    assert obj._aliases == {obj.method1: info}
    assert obj.method1 == obj.alternate_name_for_method1


# class Case0(TagManager, tag='_is_tagged'):
#     @TagManager.tag('optional info')
#     def method(self):
#         pass

# case0 = Case0()
