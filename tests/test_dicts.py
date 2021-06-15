from recipes.dict import AVDict


def test_avdict():
    av = AVDict()
    av['x']['y'] = 'z'
