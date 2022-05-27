# std
import ast

# local
from recipes.testing import Expected
from recipes.introspect.utils import get_module_name
from recipes.introspect.imports import ImportRefactory


test_get_module_name = Expected(get_module_name)({
    #
    ast.parse('import this').body[0]:                       'this',
    ast.parse('import this.that.those').body[0]:            'this.that.those',
    ast.parse('from this.that.these import them').body[0]:  'this.that.these',
    #
    '/recipes/src/recipes/string/brackets.py':      'recipes.string.brackets',
    '/recipes/src/recipes/oo/property.py':          'recipes.oo.property',
    #
    ImportRefactory:                                'recipes.introspect.imports'
})


def test_get_current_module_name():
    assert get_module_name() == 'test_utils'
