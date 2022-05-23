# Copyright 2018 Owkin, inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Packaging settings."""
import os
from codecs import open

from setuptools import find_packages
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))


with open(os.path.join(here, "README.md"), "r", "utf-8") as fp:
    readme = fp.read()


about = {}
with open(os.path.join(here, "substra", "__version__.py"), "r", "utf-8") as fp:
    exec(fp.read(), about)


setup(
    name="substra",
    version=about["__version__"],
    description="Substra CLI for interacting with substra-backend",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/SubstraFoundation/substra",
    author="Owkin",
    author_email="fldev@owkin.com",
    license="Apache 2.0",
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Utilities",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.7",
    ],
    keywords=["cli", "substra"],
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    install_requires=[
        "click>=7.1.1,!=8.0.0",  # issue with click 8.0.0 (#4)
        "requests",
        "docker",
        "consolemd",
        "pyyaml",
        "pydantic>=1.5.1",
        "six",
        "tqdm",
    ],
    python_requires=">=3.7",
    setup_requires=["pytest-runner"],
    extras_require={
        "dev": [
            "pandas",
            "pytest",
            "pytest-cov",
            "pytest-mock",
            "substratools>=0.13.0",
            "black",
            "flake8",
            "isort",
            "docstring_parser",
        ],
    },
    entry_points={
        "console_scripts": [
            "substra=substra.cli.interface:cli",
        ],
    },
    zip_safe=False,
)
