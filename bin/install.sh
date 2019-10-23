#!/bin/bash -e

python setup.py sdist
pip install dist/scraper-0.1.0.tar.gz
