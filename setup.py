#!/usr/bin/env python

from setuptools import setup, find_packages
setup(
    name = "ttr",
    version = "0.1.0",
    packages = find_packages(),
    # metadata for upload to PyPI
    author = "Andrey Volkov",
    author_email = "amadev@mail.ru",
    description = "Turbo test runner",
    license = "MIT",
    keywords = "test runner",
    url = "https://github.com/amadev/ttr",
    install_requires=[
        'inotify',
        'mock',
        'extras',
        'testtools'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities'
    ],
)
