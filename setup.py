#!/usr/bin/env python
import codecs
from os import path

from setuptools import setup


VERSION = (0, 7, 2, "final", 0)


def get_version(version=None):
    """Derives a PEP386-compliant version number from VERSION."""
    if version is None:
        version = VERSION  # pragma: nocover
    assert len(version) == 5
    assert version[3] in ("alpha", "beta", "rc", "final")

    # Now build the two parts of the version number:
    # main = X.Y[.Z]
    # sub = .devN - for pre-alpha releases
    #     | {a|b|c}N - for alpha, beta and rc releases

    parts = 2 if version[2] == 0 else 3
    main = ".".join(str(x) for x in version[:parts])

    sub = ""
    if version[3] != "final":  # pragma: no cover
        mapping = {"alpha": "a", "beta": "b", "rc": "c"}
        sub = mapping[version[3]] + str(version[4])

    return main + sub


version = get_version()

# Get the long description from the README
long_description = None
here = path.dirname(path.abspath(__file__))
with codecs.open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Install requirements
install_requires = [
    "httpx==0.7.6",
    "asynctest",
]

# Test requirements
tests_require = [
    "trio",
]

dependency_links = [
    # "git+https://github.com/encode/httpx.git@refs/pull/511/head#egg=httpx-0.7.6",
]

setup(
    name="respx",
    version=version,
    author="Jonas Lundberg",
    author_email="jonas@5monkeys.se",
    url="https://github.com/lundberg/respx",
    license="MIT",
    keywords=[
        "httpx",
        "mock",
        "responses",
        "requests",
        "async",
        "http",
        "client",
    ],
    description="A utility for mocking out the Python HTTPX library.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    packages=["respx"],
    install_requires=install_requires,
    tests_require=tests_require,
    dependency_links=dependency_links,
    test_suite="tests",
)
