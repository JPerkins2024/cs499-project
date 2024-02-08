#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from os.path import basename
from os.path import splitext
from glob import glob

from setuptools import find_packages
from setuptools import setup


def get_version():
    with open("src/ifxdevsim/version.py", "r") as f:
        version = f.read().split("=")[1].strip().replace('"', "").replace("'", "")

    return version


setup(
    name="ifxdevsim",
    author="Jeremy Wells",
    author_email="Jeremy.Wells@infineon.com",
    version=get_version(),
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    package_data={},
    zip_safe=False,
    scripts=[],
    install_requires=[
        "numpy",
        "pandas",
        "coloredlogs",
        "flatten_json",
        "frozendict",
        "cexprtk",
        "pint",
        "typing_extensions>=4.0",
        "pylatexenc",
    ],
    entry_points={"console_scripts": ["dvsim = ifxdevsim:main",]},
)
