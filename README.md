# recipes

> A cookbook for the python developer connoisseur

<!-- 
TODO
[![Build Status](https://travis-ci.com/astromancer/recipes.svg?branch=master)](https://travis-ci.com/astromancer/recipes)
[![Documentation Status](https://readthedocs.org/projects/recipes/badge/?version=latest)](https://recipes.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/recipes.svg)](https://pypi.org/project/recipes)
[![GitHub](https://img.shields.io/github/license/astromancer/recipes.svg?color=blue)](https://recipes.readthedocs.io/en/latest/license.html)
 -->

This project contains a curated collection of convenient utility functions that
are useful across many projects. The library extends the standard python
library's functionality, and is therefore similarly structured. The following
highlights the available modules and their functionality:

### Extending functionality of builtins
* string
    : _substitution, affix editing, recasing, pluralization, bracket parsing, etc._
* lists
    : _cosorting, multi-indexing, conditional splitting, flattening, deduplication._
* dicts
    : _Attribute dicts, many-to-one maps, autovivification, tree-like mappings, ordered defaultdict and various other mapping utilities_
* sets 
    : _Ordered sets_
* op 
    : _Drop in replacement for builtin `operator` module with added support for default values. And then some.'_

### Input / Output
* io 
    : _File tree iteration, context managers for safe input/output with file backups, flexible (de)serialization wrappers._
* regex
    : _Contract verbose style regexes._

### Recipes involving iterators
* iter
:   _Missing iteration utilities: cofiltering, conditional indexing, ._

### Various array functions
* array

### Functional programming
<!-- * functionals
    : _Functional decorator patterns_ -->
* decorators
    :_Extensible decorators for: Control flow (catching exceptions, fallback values), parameter/return value tracing, line profiling._
* caches
    : _Performant functional memoization._

### API Development helpers
* pprint : _Pretty Printing_
* logging 
* synonyms 
    : _Parameter name translation decorator for building flexible APIs._
* interactive
* bash

### Code Introspection
* introspect
    : _Refactor (sort, merge, split, relativize, (de)localize etc.) import statements in python source code._
    
 
### Object Oriented Tools
* oo  


### Miscellaneous
* misc   
  
* transforms  



# Install

```shell
pip install https://github.com/astromancer/recipes.git
```

# Use

## Example
```python

```


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

