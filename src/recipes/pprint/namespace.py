
"""
Pretty print object namespaces.
"""

from .. import op
from .mapping import pformat as _pformat


def pformat(target, attrs=..., maybe=(), ignore='*_', rename=(), remap=(),
            name=None, enclose='<>', **kws):
    """
    Pretty format an object's namespace (attributes, properties and their values) 

    Parameters
    ----------
    target : object
        The instance whose namespace will be represented.
    attrs : Sequence[str|ellipsis] or ellipsis, optional
        The attribute names. The default value, `...`, means use all available 
        attributes in `__slots__` or `__dict__`. To represent additional 
        properties, you can include more names with the ellipsis in a sequence
        eg: (..., 'aproperty'). This is interpreted as though the slot names
        are expanded in-place at the position of the elipsis, so order matters.
    maybe : Sequence[str], optional
        Attribute or property names to show conditionally based on the value
        of said attribute. By default ().
    ignore : str, optional
        Pattern(s) of attribute names to ignore. The default value, '*_',
        ignores all names beginning with an underscore.
    rename : dict[str], optional
        Mapping of attributes (str) that will be renamed to new names, by
        default ().  Values are kept unchanged.
    remap : dict[str], optional
        Attributes (str) whose value will be replaced by the value of a
        different attribute, by default (). Attribute names are kept unchanged.
    name : str, optional
        Object name to use. The default, None, uses the object class name.
    enclose : str, optional
        Characters used to enclose the entire representation string. The
        default, '<>', emulates results from the builtin `repr`.


    Returns
    -------
    str
        Object namespace representation.
    """

    name = name or type(target).__name__

    if remap := dict(remap):
        attrs = op.resolve_attr_names(target, attrs, ignore)
        for old, new in remap.items():
            attrs[attrs.index(old)] = new

    # fetch attribute values
    state = op.get.attrs(target, attrs, maybe, ignore)

    if rename := {**dict(rename), **dict(zip(remap.values(), remap.keys()))}:
        state = {rename.get(key, key): val for key, val in state.items()}

    opn, *close = enclose
    # if '\n' in (newline := kws.get('newline', '')):
    #     space = len(opn) + len(kws.get('brackets', '()')[0])
    #     kws['newline'] = newline + ' ' * space
    return ''.join((_pformat(state, f'{opn}{name}', **kws), *close))


# ---------------------------------------------------------------------------- #
class PrettyPrint:
    """Mixin class that pretty prints object state space from slots."""

    def __str__(self):
        return pformat(self)  # self.__class__.__name__

    def __repr__(self):
        return pformat(self)  # self.__class__.__name__

    def pformat(self, attrs=..., maybe=(), ignore='*_', name=None, enclose='<>', **kws):
        return pformat(self, attrs, maybe, ignore, name, enclose, **kws)

    def pprint(self, **kws):
        print(self.pformat(**kws))


# alias
PPrinter = Pprinter = PrettyPrint
