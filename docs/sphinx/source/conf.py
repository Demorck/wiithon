# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src")))

from wiithon import __version__


def _skip_imported_members(app, what, name, obj, skip, options):
    """Only document members actually defined in the module being processed."""
    if what != "module":
        return skip

    current = app.env.temp_data.get("autodoc:module")
    origin = getattr(obj, "__module__", None)

    if current and origin and origin != current:
        return True

    return skip


def setup(app):
    app.connect("autodoc-skip-member", _skip_imported_members)

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'wiithon'
copyright = '2026, Demorck'
author = 'Demorck'

release = __version__
version = '.'.join(release.split('.')[:2])

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

templates_path = ['_templates']
exclude_patterns = []

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# -- Autodoc -----------------------------------------------------------------

autodoc_typehints = "description"
autodoc_member_order = "bysource"

always_document_param_types = True
typehints_defaults = "comma"


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

html_theme_options = {
    "navigation_depth": 2,
    "collapse_navigation": False,
    "titles_only": True,
}