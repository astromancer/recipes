
# third-party
import anytree
from anytree.render import _is_last

# relative
from ..oo.temp import temporarily


# ---------------------------------------------------------------------------- #

class DynamicIndentRender(anytree.RenderTree):

    def __init__(self, node, style=anytree.ContRoundStyle(), childiter=list,
                 maxlevel=None, attr='name'):

        super().__init__(node, style, childiter, maxlevel)

        self.attr = str(attr)
        self.widths = [0] * (node.height + 1)
        # self.widths[0] = len(getattr(node, self.attr))
        # Adapt the style
        # Use first character of vertical/branch/end strings eg "│", "├", "└"
        style = self.style
        self.style = anytree.AbstractStyle(
            *next(zip(style.vertical, style.cont, style.end)))

    def __iter__(self):
        return self.__next(self.node, ())

    def __next(self, node, continues, level=0):
        name = str(getattr(node, self.attr))
        self.widths[level:] = [len(name), *([0] * (node.height + 1))]
        # print(f'{node.name = :<15} {level = :<10} {self.widths = !s:<20} {continues = !s:<20}')

        yield self.__item(node, continues, self.style, level)

        level += 1
        children = node.children
        if children and (self.maxlevel is None or level < self.maxlevel):
            for child, is_last in _is_last(self.childiter(children)):
                yield from self.__next(child, continues + (not is_last, ), level=level)

    def __item(self, node, continues, style, level):

        if not continues:
            return anytree.render.Row(u'', u'', node)

        selection = (style.empty, style.vertical)
        *items, last = [f'{selection[c]: <{w}}'
                        for w, c in zip(self.widths[1:], continues)]

        branches = f'{(style.end, style.cont)[continues[-1]]: <{self.widths[level + 1]}}'
        indent = ''.join(items)
        # print(f'{items = }\n{last = }\n{branches = }')

        return anytree.render.Row(indent + branches,
                                  indent + last,
                                  node)

    def by_attr(self, attrname='name'):
        with temporarily(self, attr=attrname):
            return super().by_attr(attrname)
