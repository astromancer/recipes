
# std
from pathlib import Path

# third-party
from loguru import logger

# relative
from .dicts import AttrReadItem, DictNode
from .introspect.utils import get_module_name, get_package_name


# ---------------------------------------------------------------------------- #

class ConfigNode(DictNode, AttrReadItem):

    @classmethod
    def load(cls, filename):
        return cls(**load(filename))

    @classmethod
    def load_module(cls, filename, format=None):
        config_file = find_config((path := Path(filename)), format, True)
        node = cls.load(config_file)
        candidates = get_module_name(path).split('.')[::-1]
        for parent in candidates:
            if parent in node:
                return node[parent]

        raise ValueError('Could not locate config section for any of the parent'
                         f' packages: {candidates} in config file {config_file}')

# ---------------------------------------------------------------------------- #

class ConfigLoader:

    # @classmethod
    # def hook(cls, name):
    #     obj = sys.modules[name] = cls(sys.modules[name])
    #     return obj

    def __init__(self, module, format=None):
        self.mod = module
        self.format = format
        self.config = None

    def __getattr__(self, key):
        if key == 'CONFIG':
            cfg = super().__getattr__('config')
            if cfg is None:
                self.config = cfg = ConfigNode.load(
                    find_config(self.module.__file__, self.format)
                )
            return cfg

        return super().__getattr__(key)


def find_config(filename, format=None, raises=False):
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
        logger.warning('Could not find package name for {!s}', filename)

    path = Path(filename)
    parts = path.parts
    package_root = Path('/'.join(('', *parts[1:parts.index(pkg) + 1])))
    if package_root.name == 'src':
        package_root = package_root.parent

    parent = path.parent
    extensions = [format] if format else CONFIG_PARSERS
    while parent != package_root:
        for name in extensions:
            for filename in parent.glob(f'*.{name}'):
                logger.info("Found config file: '{}' in {!r} module (sub-"
                            "folder) of package {}.", filename, parent, pkg)
                return filename

        parent = parent.parent

    message = ('Could not find config file in any of the parent folders down to'
               f' the package root for {filename = :}, {format = :}')

    if raises:
        raise FileNotFoundError(message)

    logger.debug(message)


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
