
# std
import re
import warnings
from pathlib import Path

# third-party
from loguru import logger
from platformdirs import user_config_path

# relative
from . import io
from .flow import Emit
from .io import read_lines
from .containers.dicts.node import DictNode
from .containers.dicts.core import _AttrReadItem
from .introspect.utils import get_module_name, get_package_name


# ---------------------------------------------------------------------------- #
CACHE = {}
REGEX_VERSION = re.compile(R'v?(\d+).(\d+).(.+)')


# ---------------------------------------------------------------------------- #

def search(caller, format=None, user=True, emit='error'):
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

    pkg = get_package_name(caller)
    extensions = [format] if format else tuple(CONFIG_PARSERS)

    if pkg is None:
        raise ModuleNotFoundError('Could not find package name for {!s}.', caller)

    if user:
        # Check in user config folder
        user_path = user_config_path(pkg)
        if user_path.exists():
            if filename := search_ext(user_path, extensions, pkg):
                return filename

        # raise / warn / whatever
        Emit(emit, FileNotFoundError)(
            'Could not find user config for package {} in {}', pkg, user_path
        )
        return

    #
    return search_project_tree(pkg, caller, extensions, emit)


def search_project_tree(pkg, caller, extensions, emit='error'):
    # search project source tree

    path = Path(caller)
    parts = path.parts
    package_root = Path('/'.join(('', *parts[:-parts[::-1].index(pkg)])))

    logger.debug('Searching {} project tree: {}', pkg, package_root)
    if filename := search_ext(package_root, extensions, pkg):
        return filename

    # raise / warn / whatever
    Emit(emit, FileNotFoundError)(
        'Could not find config file in any of the parent folders up to'
        ' the package root for filename = {!s}, extensions = {}.',
        path, extensions
    )

    # if package_root.name == 'src':
    #     package_root = package_root.parent

    # logger.debug('Searching project tree: {}', package_root)
    # #
    # if filename := _search_upward(path, extensions, package_root, pkg):
    #     return filename


def _search_upward(path, extensions, root, pkg=''):
    parent = path.parent
    while True:
        if filename := search_ext(parent, extensions, pkg):
            return filename

        # if root we are done
        if parent == root:
            return

        # step up
        parent = parent.parent


def search_ext(folder, extensions, pkg=''):
    if filename := next(io.iter_files(folder, extensions, True), None):
        logger.info("Found config file for package: {!r} at '{}'.",
                    pkg, filename)
        return filename


# Load
# ---------------------------------------------------------------------------- #

def load_yaml(filename):
    import yaml

    with filename.open('r') as file:
        return yaml.safe_load(file)  # Loader=yaml.FullLoader


def load_ini(filename):
    from configparser import ConfigParser

    config = ConfigParser()
    config.read(filename)
    return config


CONFIG_PARSERS = {
    'yaml': load_yaml,
    'yapf': load_ini,
    'ini': load_ini,
}


def load(filename):
    if filename not in CACHE:
        CACHE[filename] = _load(filename)

    return CACHE[filename]


def _load(filename):
    if (path := Path(filename)).exists():
        return CONFIG_PARSERS[path.suffix.lstrip('.')](path)

    raise FileNotFoundError(f"Non-existent file: '{filename!s}'")


def load_for(filename):
    if filename := search(filename):
        return load(filename)
    return {}


# Create
# ---------------------------------------------------------------------------- #

def create_user_config(filename, caller, overwrite=None, version_stamp=''):

    pkg = get_package_name(caller)
    source = Path(caller).parent / filename

    # auto-fill version
    if version_stamp is True:
        from importlib.metadata import version

        version_stamp = str(version(pkg))

    # get path
    configpath = user_config_path(pkg) / filename

    # existing user config
    if configpath.exists():
        if overwrite is None:
            overwrite = _should_overwrite(configpath, version_stamp)

        if overwrite is False:
            return configpath

    # new user config
    return _create_user_config(pkg, configpath, source, overwrite, version_stamp)


def _should_overwrite(configpath, version_stamp):

    if not version_stamp:
        return False

    # check latest version
    version = map(REGEX_VERSION.search, read_lines(configpath, 5))
    if version := next(filter(None, version), None):
        version_stamp = REGEX_VERSION.match(version_stamp)
        for current, incoming in zip(version.groups(), version_stamp.groups()):
            if current > incoming:
                return False
        return True

    else:
        logger.warning(
            'No version info found in {}. Overwriting from source at version {}.',
            configpath, version_stamp
        )
        return True


def _create_user_config(pkg, path, source=None, overwrite=None,
                        version_stamp=''):

    # first time import? Create user config!

    if source is None:
        source = Path(__file__).parent / path.name

    if not (source := Path(source)).exists():
        raise FileNotFoundError(
            f'Config file source {source!s} does not exist!')

    if (exists := path.exists()) and overwrite is False:
        logger.info('User config for {} already exisits at: {!s}. Won\'t '
                    'overwrite this file unless requested.', pkg, path)
        return

    #
    logger.info('{} user config for {}: {!s}.',
                ('Creating', 'Overwriting')[exists], pkg, path)

    # read source config
    text = source.read_text()

    # check version stamp
    if version_stamp:
        if '{version}' not in text:
            raise ValueError(f'"{{version}}" not in source: {source}.')

        # add v marker
        if not version_stamp.startswith('v'):
            version_stamp = f'v{version_stamp}'

        logger.info('Adding version stamp: {!s}.', version_stamp)
        text = text.replace('{version}', version_stamp, 1)

    elif '{version}' in text:
        warnings.warn(f'Config for {pkg}: {source!s} contains "{{version}}" '
                      'but null `version_stamp` was provided.')

    # create backup (if overwriting) and write new config file
    with io.backed_up(path, folder=path.parent) as fp:
        fp.write(text)

    return path


# Node
# ---------------------------------------------------------------------------- #

class ConfigNode(DictNode, _AttrReadItem):

    @classmethod
    def load(cls, filename, defaults=None):
        assert filename or defaults
        config = load(defaults) if defaults else {}
        if filename and Path(filename).exists():
            config.update(**load(filename))
        return cls(config)

    @classmethod
    def load_module(cls, filename, format=None):

        path = Path(filename)
        user_config_file = search(path, format, True, 'silent')
        source_config_file = search(path, format, False)
        node = cls.load(user_config_file, source_config_file)

        # step up parent modules
        candidates = get_module_name(path).split('.')

        if ('config' in (path.parent.name, path.stem)
                or (path.stem == '__init__' and len(candidates) == 1)):
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
        raise ValueError(
            f'Config file {user_config_file or source_config_file} does not '
            'contain any section matching module names in the package tree: '
            f'{candidates}\nThe following config sections are available: '
            f'{nl.join(("", *map(repr, keys)))}'
        )

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
#                     search(self.module.__file__, self.format)
#                 )
#             return cfg

#         return super().__getattr__(key)


# ---------------------------------------------------------------------------- #
