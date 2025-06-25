# --------------------------------------------
# Setup file for the package
#
# JL Diaz (c) 2019
# --------------------------------------------

import os

from setuptools import find_packages, setup

from setuptools import find_packages, setup


def read_file(fname: str) -> str:
    """Read a local file."""
    return (Path(__file__).parent / fname).read_text(encoding="utf-8")


setup(
    name="tags-macros-plugin",
    version="0.2.0",
    description="Processes tags in yaml metadata",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    keywords="mkdocs python markdown tags",
    url="",
    author="JL Diaz",
    author_email="jldiaz@gmail.com",
    license="MIT",
    python_requires=">=3.6",
    install_requires=[
        "mkdocs>=0.17",
        "jinja2",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
    ],
    packages=find_packages(exclude=["*.tests"]),
    package_data={"tags": ["templates/*.md.template"]},
    entry_points={"mkdocs.plugins": ["tags = tags.plugin:TagsPlugin"]},
)
