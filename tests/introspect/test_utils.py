
# std
import ast

# local
from recipes.testing import Expected
from recipes.introspect.imports import ImportRefactory
from recipes.introspect.utils import get_module_name, get_package_name


def parse(code):
    return ast.parse(code).body[0]


test_get_package_name = Expected(get_package_name)({
    #
    parse('import this'):                           'this',
    parse('import this.that.those'):                'this',
    parse('from this.that.these import them'):      'this',
    #
    '/recipes/src/recipes/string/brackets.py':      'recipes',
    '/recipes/src/recipes/oo/property.py':          'recipes',
    #
    ImportRefactory:                                'recipes',
})

test_get_module_name = Expected(get_module_name)({
    #
    parse('import this'):                           'this',
    (parse('import this'), 1):                      'this',
    parse('import this.that.those'):                'this.that.those',
    (parse('import this.that.those'), 1):           'those',
    parse('from this.that.these import them'):      'this.that.these',
    (parse('from this.that.these import them'), 1): 'these',
    #
    '/recipes/src/recipes/string/brackets.py':      'recipes.string.brackets',
    ('/recipes/src/recipes/string/brackets.py', 1): 'brackets',
    '/recipes/src/recipes/oo/property.py':          'recipes.oo.property',
    ('/recipes/src/recipes/oo/property.py', 1):     'property',
    #
    ImportRefactory:                                'recipes.introspect.imports',
    (ImportRefactory, 1):                           'imports'
})


def test_get_current_module_name():
    assert get_module_name() == 'test_utils'
