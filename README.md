# recipes

> A cookbook for the python developer connoisseur 🐍 📖 🍾

<!-- 
TODO
[![Build Status](https://travis-ci.com/astromancer/recipes.svg?branch=master)](https://travis-ci.com/astromancer/recipes)
[![Documentation Status](https://readthedocs.org/projects/recipes/badge/?version=latest)](https://recipes.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/recipes.svg)](https://pypi.org/project/recipes)
[![GitHub](https://img.shields.io/github/license/astromancer/recipes.svg?color=blue)](https://recipes.readthedocs.io/en/latest/license.html)
 -->

This project contains a curated collection of convenient utility functions that
are useful across many projects. The library extends many of the python builtin
modules' functionalities, and is therefore similarly structured.


Below are some highlights of the available modules and their functionality:


## Recipes extending builtins
* [`strings`](https://github.com/astromancer/recipes/tree/main/src/recipes/string)
    : _substitution, character deletion, affix editing, case switching, pluralization,
      similarity matching, bracket parsing, and more ...
* [`lists`](https://github.com/astromancer/recipes/tree/main/src/recipes/lists)
    : _co-sorting, multi-indexing, conditional splitting, deduplication._
* [`dicts`](https://github.com/astromancer/recipes/tree/main/src/recipes/dicts)
    - [`core`](https://github.com/astromancer/recipes/tree/main/src/recipes/dicts/core.py)
        : _Attribute dicts, many-to-one maps, autovivification, tree-like mappings,
        ordered defaultdict, pretty printing, and various other mapping utilities._
    - [`node`]()
        : A powerful dictionary node object for creating and manipulating data trees.
* [`sets`](https://github.com/astromancer/recipes/tree/main/src/recipes/sets) 
    : _Ordered sets_
* [`op`](https://github.com/astromancer/recipes/tree/main/src/recipes/op) 
    : _Drop in replacement for the builtin `operator` module with added support
     for default values. And then some._

## Iterators / Generators
* [`iter`](https://github.com/astromancer/recipes/tree/main/src/recipes/iter)
:   _Additional iteration utilities: co-filtering, conditional indexing._

## Functional programming
* [`functionals`](https://github.com/astromancer/recipes/tree/main/src/recipes/functionals)
    : Funtional utilities: Factory for creating callables with any signature;
     partial functions definitions via parameter placeholder syntax.
* [`decorators`](https://github.com/astromancer/recipes/tree/main/src/recipes/decorators)
    : _Extensible decorators for: Control flow (catching exceptions, fallback
    values), parameter/return value tracing, line profiling._
* [`caching`](https://github.com/astromancer/recipes/tree/main/src/recipes/caching)
    : _Performant functional memoization._

## Object Oriented Tools
* [`oo`](https://github.com/astromancer/recipes/tree/main/src/recipes/oo)
    : _Cached property decorator (with optional dependencies), property forwarding for nested objects,
      constructors for objects employing `__slots__`, context manager for temporary attribute setting._
    - [`meta`]()
        : Tools for building classes, function tagging.


## API and Development helpers
* [`api`](https://github.com/astromancer/recipes/tree/main/src/recipes/api)
    - [`synonyms`](https://github.com/astromancer/recipes/tree/main/src/recipes/api/synonyms) 
        : _Intelligent parameter name autocorrect decorator for building flexible APIs._
* [`pprint`](https://github.com/astromancer/recipes/tree/main/src/recipes/pprint)
     : _pretty printing!_
* [`logging`](https://github.com/astromancer/recipes/tree/main/src/recipes/logging) 
    : _logging mixin for explicitly tracing class functionality._
<!--     
* [`bash`](https://github.com/astromancer/recipes/tree/main/src/recipes/bash)
    : _bash style brace expansion and contraction._ -->
<!-- * [`interactive`](https://github.com/astromancer/recipes/tree/main/src/recipes/interactive) -->
<!-- * [`regex`](https://github.com/astromancer/recipes/tree/main/src/recipes/regex)
    : _Contract verbose style regexes._ -->

## Input / Output
* [`io`](https://github.com/astromancer/recipes/tree/main/src/recipes/io) 
    : _File tree iteration, context managers for safe input/output with file
     backups, flexible (de)serialization wrappers._


## Code Introspection
* [`introspect`](https://github.com/astromancer/recipes/tree/main/src/recipes/introspect)
    : Inspect python objects.
    - [`imports`](https://github.com/astromancer/recipes/tree/main/src/recipes/introspect/imports)
        : _Refactor (sort, merge, split, relativize, (de)localize etc.) import 
        statements in python source code._
    

## Math
* [`transforms`](https://github.com/astromancer/recipes/tree/main/src/recipes/transforms) 
    : _Transforms to and from Cartesian, Spherical, Cylindrical coordinates._

## Arrays
* [`array`](https://github.com/astromancer/recipes/tree/main/src/recipes/array)
    - [`fold`](https://github.com/astromancer/recipes/tree/main/src/recipes/array/fold)
    : _Array folding (windowing) with minimal memory duplication._


# Install

```shell
python -m pip install https://github.com/astromancer/recipes
```

<!-- # Use -->

<!-- ## Example
```python

``` -->


<!-- ![Example Image](https://github.com/astromancer/recipes/blob/master/tests/images/example_0.png "Example Image") -->


<!-- For more examples see [Documentation]() -->

<!-- # Documentation -->


# Test

The [`test suite`](./tests) contains further examples of how
`recipes` can be used.  Testing is done with `pytest`:

```shell
pytest recipes
```

# Contribute
Contributions are welcome!

1. [Fork it!](https://github.com/astromancer/recipes/fork)
2. Create your feature branch\
    ``git checkout -b feature/rad``
3. Commit your changes\
    ``git commit -am 'Add some cool feature  😎'``
4. Push to the branch\
    ``git push origin feature/rad``
5. Create a new Pull Request

# Contact

* e-mail: hannes@saao.ac.za

<!-- ### Third party dependencies
 * see [LIBRARIES](https://github.com/username/sw-name/blob/master/LIBRARIES.md) files -->

# License

* see [LICENSE](https://github.com/astromancer/recipes/blob/master/LICENSE)


<!-- # Version
This project uses a [semantic versioning](https://semver.org/) scheme. The 
latest version is
* 0.1.0 -->

