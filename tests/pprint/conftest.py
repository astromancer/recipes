# content of conftest.py

# from typing import Dict, Tuple
# import pytest
import re


def testid(item):
    if item.function.__name__.startswith('test_caller'):
        return re.search(r'\[([^]]+)\]', item.name)[1]
    return ''


def pytest_collection_modifyitems(session, config, items):
    items.sort(key=testid)
