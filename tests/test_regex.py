# third-party
import pytest

# local
from recipes.regex import RGX_VERBOSE_FLAG, terse


@pytest.mark.parametrize(
  'pattern, cleaned',
  [('(?aiLmsux)', '(?aiLmsu)'),
  ('(?axiu)', '(?aiu)'),
  ('(?x)', ''),
  ('(?sm)(stuff!)', '(?sm)(stuff!)')]
  )
def test_find_verbose_flag(pattern, cleaned):
    assert RGX_VERBOSE_FLAG.sub(r'\1\2\3', pattern) == cleaned

@pytest.mark.parametrize(
    'pattern',
    [r"""
      [0-9]            # 1 Number
      [A-Z]            # 1 Uppercase Letter
      [a-y]            # 1 lowercase, but not z
      z                # gotta have z...
      """]
)
def test_terse(pattern):
    print(terse(pattern))
