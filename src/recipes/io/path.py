import re
from pathlib import Path


def false(_):
    return False


class Path(type(Path())):  # HACK to get proper path type on all systems
    def reglob(self, exp, ignore=None):
        """
        Filename matching with regular expressions

        Parameters
        ----------
        exp : str
            Regular expression for matching a filename
        ignore : str or list, optional
            Regular expression or list of filenames to ignore, by default None

        Yields
        ------
        Path
            The matching paths
        """
        include = re.compile(exp)
        exclude = false
        if isinstance(ignore, (list, tuple)):
            exclude = ignore.__contains__
        elif isinstance(ignore, str):
            exclude = re.compile(ignore).fullmatch
        elif ignore:
            raise TypeError('Ignore pattern or list is of invalid type')

        for p in self.iterdir():
            mo = include.fullmatch(p.name)
            if mo and not exclude(p.name):
                yield self / mo.group()
