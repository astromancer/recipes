import re
import pathlib

class Path(type(pathlib.Path())):  #HACK!
    def reglob(self, exp):
        '''
        glob.glob() style searching with regex

        :param exp: Regex expression for filename
        '''
        m = re.compile(exp)
        
        names = map(lambda p: p.name, self.iterdir())
        res = filter(m.match, names)
        res = map(lambda p: self/p, res)

        return res