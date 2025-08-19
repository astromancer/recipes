# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


from setuptools_scm import get_version

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'recipes'
copyright = '2025, Hannes Breytenbach'
author = 'Hannes Breytenbach'

# The full version, including alpha/beta/rc tags.
release = get_version(root='../..', relative_to=__file__)
# The short X.Y.Z version.
version = '.'.join(release.split('.')[:3])


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
]

templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['build']


# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = False


# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'renku'
html_static_path = ['_static']


# If a function's signature length in characters exceeds the number set, each
# parameter within the signature will be displayed on an individual logical
# line.
maximum_signature_line_length = 80


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'python': ('https://docs.python.org/3/', None)}


# -- Options for autodoc ----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#configuration

# Automatically extract typehints when specified and place them in
# descriptions of the relevant function/method.
autodoc_typehints = 'description'

# Don't show class signature with the class' name.
autodoc_class_signature = 'separated'


# Define the order in which automodule and autoclass members are listed
autodoc_member_order = 'bysource'

# If a function's signature length in characters exceeds the number set, each
# parameter within the signature will be displayed on an individual logical
# line.
maximum_signature_line_length = 80