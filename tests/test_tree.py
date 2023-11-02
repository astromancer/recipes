
# third-party
import pytest

# local
from recipes.tree import DynamicIndentRender, Node

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

render1 = """
├Domitian-
│        ├Bold
│        │   ├.otf
│        │   ╰Italic.otf
│        ├Italic.otf
│        ╰Roman.otf
╰EBGaramond-
           ├Bold
           │   ├.otf
           │   ╰Italic.otf
           ├ExtraBold
           │        ├.otf
           │        ╰Italic.otf
           ├I
           │├nitials.otf
           │╰talic.otf
           ├Medium
           │     ├.otf
           │     ╰Italic.otf
           ├Regular.otf
           ╰SemiBold
                   ├.otf
                   ╰Italic.otf\
"""

# @pytest.fixture()


def test_from_list():
    Node.from_list(case1)


# def test_from_dict():
#     ''


def test_dynamic_space_render():

    root = Node.from_list(case1)
    render = DynamicIndentRender(root)
    
    assert render.by_attr('name') == render1
    assert str(render) == render1
