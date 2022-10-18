from recipes.oo.meta import tagger


Mixin, method_tagger = tagger.factory('mytag')


class _TestCaseMethodTagger(Mixin):
    @method_tagger('info')
    def method1(self, *args):
        return args


def test_method_tagger():
    assert _TestCaseMethodTagger().method1.mytag == ('info', )
