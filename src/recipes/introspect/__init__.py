
# relative
from ..config import ConfigNode, find_config
from .utils import *


CONFIG = ConfigNode.load(find_config(__file__, 'yaml'))
