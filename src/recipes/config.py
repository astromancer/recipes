
# std
import re
import shutil
from pathlib import Path

# third-party
from loguru import logger
from platformdirs import user_config_path

# relative
from .utils import *
from .flow import Emit
from .io import read_lines
from .dicts.node import DictNode
from .dicts.core import _AttrReadItem
from .introspect.utils import get_module_name, get_package_name


# ---------------------------------------------------------------------------- #
CACHE = {}

REGEX_VERSION = re.compile(R'v?(\d+).(\d+).(.+)')

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
        raise ValueError(
            f'Config file {config_file} does not contain any section matching '
            f'module names in the package tree: {candidates}\nThe following '
            f'config sections are available: {nl.join(("", *map(repr, keys)))}'
        )

    def __getattr__(self, key):
        """
        Try to get the value in the dict associated with key `key`. If `key`
        is not a key in the dict, try get the attribute from the parent class.
        Note: LeafNodes
        """
        return super().__getitem__(key) if key in self else super().__getattribute__(key)


# ---------------------------------------------------------------------------- #

def create_user_config(filename, caller, overwrite=None, version_stamp=''):

    pkg = get_package_name(caller)
    source = Path(caller).parent / filename

    configpath = user_config_path(pkg) / filename
    if configpath.exists():
        if overwrite is None:
            overwrite = _should_overwrite(configpath, version_stamp)

        if overwrite is False:
            return configpath

    #
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
        raise FileNotFoundError(f'Config file source {source!s} does not exist!')

    logger.info('Creating user config: {!s}.', path)

    if version_stamp:
        text = source.read_text()
        if not '{version}' in text:
            raise ValueError(f'"{{version}}" not in source: {source}.')

        # add v marker
        if not version_stamp.startswith('v'):
            version_stamp = f'v{version_stamp}'

        logger.info('Adding version stamp: {!s}.', version_stamp)
        path.write_text(text.format(version=version_stamp))
    else:
        shutil.copy(str(source), str(path))

    return path


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
    extensions = [format] if format else CONFIG_PARSERS

    pkg = get_package_name(filename)
    if pkg is None:
        logger.warning('Could not find package name for {!s}.', filename)
    else:
        # Check in user config folder
        if found := search_ext(user_config_path(pkg), extensions):
            return found

    # search project source tree
    path = Path(filename)
    parts = path.parts
    package_root = Path('/'.join(('', *parts[1:parts.index(pkg) + 1])))
    if package_root.name == 'src':
        package_root = package_root.parent

    #
    filename = search_upward(path, extensions, package_root, pkg)
    if filename:
        return filename

    # raise / warn / whatever
    Emit(emit, FileNotFoundError)(
        'Could not find config file in any of the parent folders down to'
        ' the package root for {filename = :}, {format = :}',
        filename, format
    )


def search_upward(path, extensions, root, pkg=''):
    parent = path.parent
    while True:
        if filename := search_ext(parent, extensions, pkg):
            return filename

        # if root we are done
        if parent == root:
            break

        # step up
        parent = parent.parent


def search_ext(path, extensions, pkg=''):
    for ext in extensions:
        logger.debug('Searching: {} for *.{}', path, ext)
        for filename in path.glob(f'*.{ext}'):
            logger.info("Found config file: '{}' in {!r} module (sub-"
                        "folder) of package {}.", filename, path, pkg)
            return filename


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
        try:
            return CONFIG_PARSERS[path.suffix.lstrip('.')](path)
        except Exception as err:
            import sys
            import textwrap
            from IPython import embed
            from better_exceptions import format_exception
            embed(header=textwrap.dedent(
                f"""\
                    Caught the following {type(err).__name__} at 'config.py':184:
                    %s
                    Exception will be re-raised upon exiting this embedded interpreter.
                    """) % '\n'.join(format_exception(*sys.exc_info()))
            )
            raise

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
