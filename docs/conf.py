import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath('..'))

project = 'vaser'
author = 'Sebastien Riou'
copyright = f'{datetime.now():%Y}, {author}'
release = 'latest'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}
autodoc_member_order = 'bysource'
