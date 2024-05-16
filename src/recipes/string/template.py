'''
Template strings with some added niceties :)
'''

from string import Template


class Template(Template):

    def __init__(self, template):
        super().__init__(str(template))

    def __repr__(self):
        return f'{type(self).__name__}({self.template})'

    def __str__(self):
        return self.template

    def get_identifiers(self):
        # NOTE: python 3.11 has Template.get_identifiers
        _, keys, *_ = zip(*self.pattern.findall(self.template))
        return keys

    def sub(self, partial=False, **kws):
        if partial:
            return type(self)(self.safe_substitute(**kws))
        else:
            return self.substitute(**kws)
