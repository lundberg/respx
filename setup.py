#!/usr/bin/env python
from pathlib import Path

from setuptools import setup

exec(Path("respx", "__version__.py").read_text())  # Load __version__ into locals

setup(
    name="respx",
    version=locals()["__version__"],
    license="BSD",
    author="Jonas Lundberg",
    author_email="jonas@5monkeys.se",
    url="https://github.com/lundberg/respx",
    keywords=["httpx", "httpcore", "mock", "responses", "requests", "async", "http"],
    description="A utility for mocking out the Python HTTPX and HTTP Core libraries.",
    long_description=Path("README.md").read_text("utf-8"),
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
    package_data={"httpx": ["py.typed"]},
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.6",
    install_requires=["httpx>=0.13,<0.14", "asynctest"],
)
