# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=no-self-use
# pylint: disable=redefined-outer-name


# std libs
from recipes.introspect.imports import refactor, NodeFilter
from recipes.string import remove_prefix
import pytest
import ast
from textwrap import dedent
from pathlib import Path

# local libs
from recipes.testing import Expected, expected, mock, ECHO, PASS, Warns

from recipes.introspect.imports import ImportCapture, ImportFilter, ImportRefactory, ImportMerger, rewrite, tidy

from recipes.introspect.imports import ImportSplitter, Parentage, ImportRelativizer
TESTPATH = Path(__file__).parent.absolute()