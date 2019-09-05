import sys
from glob import glob

from setuptools import find_packages, setup
import os
pjoin = os.path.join

here = os.path.abspath(os.path.dirname(__file__))

packages = []
for d, _, _ in os.walk('scraper'):
    if os.path.exists(pjoin(d, '__init__.py')):
        packages.append(d.replace(os.path.sep, '.'))

# Version
ns = {}
with open(pjoin(here, 'scraper', '_version.py')) as f:
    exec(f.read(), {}, ns)


def setup_package():

    metadata = dict(
        name                = 'scraper',
    	packages            = packages,
    	description         = """Media Scraper Library.""",
    	author              = "olbap-selrach",
    	platforms           = "Linux",
        version             = ns['__version__'],
    	keywords            = ['Interactive', 'Interpreter', 'Shell', 'Web'],
    	classifiers         = ['Programming Language :: Python :: 3'],
    )


    setup(**metadata)


if __name__ == '__main__':
    setup_package()