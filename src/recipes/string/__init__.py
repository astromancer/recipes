"""
Utilites for woking with strings.
"""

from . import delimited
from .template import Template
from .percentage import Percentage
from .stacking import hstack, vstack, width
from .justify import justify, overlay, resolve_justify
from .plurals import naive_english_plural, named_items, numbered, pluralize
from .casing import (camel_case, kebab_case, monospaced, pascal_case,
                     snake_case, strike, title, has_upper)
from .utils import (backspaced, indent, insert, most_similar, csv,
                    partition_whitespace, reindent, similarity, strings,
                    strip_non_ascii, sub, surround, truncate)
from .affixes import (remove_affix, remove_prefix, remove_suffix,
                      remove_suffixes, replace_prefix, replace_suffix,
                      shared_affix, shared_prefix, shared_suffix)
# alias
delim = delimited
