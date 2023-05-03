# std
from pathlib import Path

# third-party
from loguru import logger

# relative
from .introspect.utils import get_package_name

# local
from recipes.dicts import AttrReadItem, DictNode

# ---------------------------------------------------------------------------- #


class ConfigNode(DictNode, AttrReadItem):

    @classmethod
    def load(cls, filename):
        return cls(**load(filename))


# ---------------------------------------------------------------------------- #
def find_config(filename, style=None):  # , root='src'

    pkg = get_package_name(filename)
    if pkg is None:
        logger.warning('Could not find package name for {!s}', filename)

    path = Path(filename)
    parts = path.parts
    package_root = Path('/'.join(('', *parts[1:parts.index(pkg)])))
    if package_root.name == 'src':
        package_root = package_root.parent

    parent = path.parent
    extensions = [style] or CONFIG_PARSERS
    while parent != package_root:
        for name in extensions:
            for filename in parent.glob(f'*.{name}'):
                logger.info("Found config file: '{}'", filename)
                return filename

        parent = parent.parent

    logger.debug("No local config file found for '{}'", filename)


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
