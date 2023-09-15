
from recipes.decorators import update_defaults


@update_defaults(dict(nwindow=1,
                  noverlap=2,
                  kmax=3))
def flag_outliers(bjd, flux,
                  nwindow=0,
                  noverlap=0,
                  kmax=0):
    pass


def test_update_defaults():
    assert flag_outliers.__defaults__ = (1,2,3)