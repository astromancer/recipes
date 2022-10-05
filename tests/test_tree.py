
from recipes.tree import DynamicRender, Node
import pytest

case1 = ['Domitian-Bold.otf',
         'Domitian-BoldItalic.otf',
         'Domitian-Italic.otf',
         'Domitian-Roman.otf',
         'EBGaramond-Bold.otf',
         'EBGaramond-BoldItalic.otf',
         'EBGaramond-ExtraBold.otf',
         'EBGaramond-ExtraBoldItalic.otf',
         'EBGaramond-Initials.otf',
         'EBGaramond-Italic.otf',
         'EBGaramond-Medium.otf',
         'EBGaramond-MediumItalic.otf',
         'EBGaramond-Regular.otf',
         'EBGaramond-SemiBold.otf',
         'EBGaramond-SemiBoldItalic.otf']

# @pytest.fixture()


def string_data_tree():
    return Node.from_list(case1)


def test_dynamic_space_render(string_data_tree):
    r = DynamicRender(string_data_tree)
    # from IPython import embed
    # embed(header="Embedded interpreter at 'tests/test_tree.py':28")
    print(r.by_attr("name"))
    print(r)


test_dynamic_space_render(string_data_tree())
