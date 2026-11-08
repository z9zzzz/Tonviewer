"""Sphinx configuration for Tonviewer documentation."""

import sys
from pathlib import Path

# Make the src-layout package importable for Sphinx autodoc.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

project = "Tonviewer"
author = "Tonviewer contributors"
release = "1.3.1"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "myst_parser",
]

autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_title = "Tonviewer Documentation"

html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "titles_only": False,
}

# Accept both reStructuredText and Markdown source files.
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
