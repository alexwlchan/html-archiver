#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import codecs

from setuptools import setup

here = os.path.dirname(os.path.abspath(__file__))

with codecs.open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

if sys.argv[-1] == "publish":
    os.system("python setup.py sdist bdist_wheel upload")
    sys.exit()

setup(
    name='html-archiver',
    version='0.1.0',
    description='Creating self-contained HTML archives of webpages',
    long_description=long_description,
    author='Alex Chan',
    author_email='alex@alexwlchan.net',
    url='https://github.com/alexwlchan/html-archiver',
    py_modules=['html_archiver'],
    install_requires=[
        'beautifulsoup4>=4.5.3,<5',
        'requests>=2.13.0,<3',
        'requests-toolbelt>=0.7.1,<1',
    ],
    license='MIT',
    classifiers=(
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'Topic :: System :: Archiving :: Backup',
        'Topic :: System :: Archiving',
    ),
)
