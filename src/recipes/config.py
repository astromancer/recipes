
# std
from pathlib import Path

# third-party
from loguru import logger

# relative
from .flow import Emit
from .dicts.node import DictNode
from .dicts.core import _AttrReadItem
from .introspect.utils import get_module_name, get_package_name


# ---------------------------------------------------------------------------- #
CACHE = {}

# ---------------------------------------------------------------------------- #


class ConfigNode(DictNode, _AttrReadItem):

    @classmethod
    def load(cls, filename):
        if filename not in CACHE:
            CACHE[filename] = cls(**load(filename))

        return CACHE[filename]

    @classmethod
    def load_module(cls, filename, format=None):
        config_file = find_config((path := Path(filename)), format, True)
        node = cls.load(config_file)

        # step up parent modules
        candidates = get_module_name(path).split('.')

        stem = Path(filename).stem
        if (stem == 'config') or (stem == '__init__' and len(candidates) == 1):
            # the package initializer is loading the config
            return node

        found = False
        keys = node.keys()
        for parent in candidates[1:]:  # can skip root here
            if parent in node:
                found = True
                node = node[parent]

        if found:
            return node

        nl = '\n    '
        raise ValueError(f'Config file {config_file} does not contain any section'
                         f' matching module names in the package tree: {candidates}\n'
                         'The following config sections are available:'
                         f' {nl.join(("", *map(repr, keys)))}')

    def __getattr__(self, key):
        """
        Try to get the value in the dict associated with key `key`. If `key`
        is not a key in the dict, try get the attribute from the parent class.
        Note: LeafNodes
        """
        return super().__getitem__(key) if key in self else super().__getattribute__(key)

# ---------------------------------------------------------------------------- #


# class ConfigLoader:

#     # @classmethod
#     # def hook(cls, name):
#     #     obj = sys.modules[name] = cls(sys.modules[name])
#     #     return obj

#     def __init__(self, module, format=None):
#         self.module = module
#         self.format = format
#         self.config = None

#     def __getattr__(self, key):
#         if key == 'CONFIG':
#             cfg = super().__getattr__('config')
#             if cfg is None:
#                 self.config = cfg = ConfigNode.load(
#                     find_config(self.module.__file__, self.format)
#                 )
#             return cfg

#         return super().__getattr__(key)


# ---------------------------------------------------------------------------- #

def find_config(filename, format=None, emit=logger.debug):
    """
    Search upwards in the folder tree for a config file matching the requested
    format.

    Parameters
    ----------
    filename : str or Path
        The filename, typically for the current file, ie. `__file__`. The parent
        folder of this file is the starting point for the search.
    format : str, optional
        The file format, by default None.

    Returns
    -------
    Path or None
        The config file if any exist.
    """

    pkg = get_package_name(filename)
    if pkg is None:
        logger.warning('Could not find package name for {!s}.', filename)

    path = Path(filename)
    parts = path.parts
    package_root = Path('/'.join(('', *parts[1:parts.index(pkg) + 1])))
    if package_root.name == 'src':
        package_root = package_root.parent

    parent = path.parent
    extensions = [format] if format else CONFIG_PARSERS
    while True:
        for name in extensions:
            logger.debug('Searching: {} for *.{}', parent, name)
            for filename in parent.glob(f'*.{name}'):
                logger.info("Found config file: '{}' in {!r} module (sub-"
                            "folder) of package {}.", filename, parent, pkg)
                return filename

        if parent == package_root:
            break

        parent = parent.parent

    # raise / warn / whatever
    Emit(emit, FileNotFoundError)(
        'Could not find config file in any of the parent folders down to'
        ' the package root for {filename = :}, {format = :}',
        filename, format
    )


def load_yaml(filename):
    import yaml

    with filename.open('r') as file:
        return yaml.safe_load(file)  # Loader=yaml.FullLoader


def load_ini(filename):
    from configparser import ConfigParser

    config = ConfigParser()
    config.read(filename)
    return config


def load(filename):
    if (path := Path(filename)).exists():
        return CONFIG_PARSERS[path.suffix.lstrip('.')](path)

    raise FileNotFoundError(f"Non-existent file: '{filename!s}'")


def load_config_for(filename):
    if filename := find_config(filename):
        return CONFIG_PARSERS[filename.suffix.rstrip('.')](filename)

    return {}


CONFIG_PARSERS = {
    'yaml': load_yaml,
    'yapf': load_ini,
    'ini': load_ini,
}
