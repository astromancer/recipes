# content of conftest.py

# from typing import Dict, Tuple
# import pytest
import re


def testid(item):
    return re.search(r'\[([^]]+)\]', item.name)[1]


def pytest_collection_modifyitems(session, config, items):
    items.sort(key=testid)
