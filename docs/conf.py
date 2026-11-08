"""Sphinx configuration for Tonviewer documentation."""

import sys
from pathlib import Path

# Make the src-layout package importable for Sphinx autodoc.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from tonviewer import __version__

project = "Tonviewer"
author = "Tonviewer contributors"
release = __version__
version = release
root_doc = "index"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "myst_parser",
]

autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"
myst_heading_anchors = 3

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_title = "Tonviewer Documentation"
html_short_title = "Tonviewer"
html_logo = "_static/ton-mark.svg"
html_favicon = "_static/ton-mark.svg"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_show_sourcelink = False

html_theme_options = {
    "navigation_depth": 3,
    "collapse_navigation": True,
    "sticky_navigation": True,
    "titles_only": False,
    "includehidden": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": True,
    "style_nav_header_background": "#0b2438",
    "version_selector": True,
    "language_selector": False,
}

html_context = {
    "display_github": True,
    "github_user": "z9zzzz",
    "github_repo": "Tonviewer",
    "github_version": "master",
    "conf_py_path": "/docs/",
}

# Accept both reStructuredText and Markdown source files.
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
