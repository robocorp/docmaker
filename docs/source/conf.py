# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Template"
copyright = ""
author = ""

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc"]

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]
html_extra_path = ["include"]
html_css_files = ["custom.css"]
html_js_files = ["iframeResizer.min.js", "custom.js"]


# -- Override Robot Framework lexer ------------------------------------------
from robotframeworklexer import RobotFrameworkLexer
from sphinx.highlighting import lexers

lexers["robotframework"] = RobotFrameworkLexer()
