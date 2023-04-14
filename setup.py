# Copyright 2022-2023 Laurent Defert
#
#  This file is part of SOSSE.
#
# SOSSE is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# SOSSE is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with SOSSE.
# If not, see <https://www.gnu.org/licenses/>.

from setuptools import setup, find_namespace_packages
import os


def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths


setup(
    name='SOSSE',
    version='0.1',
    packages=find_namespace_packages(include=['se', 'se.*', 'sosse', 'sosse.*']),

    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    include_package_data=True,
    package_data={'': package_files('se/static') + package_files('se/templates')},

    # metadata to display on PyPI
    author="Laurent Defert",
    author_email="laurent_defert@yahoo.fr",
    description="Selenium Open Source Search Engine",
    keywords="search engine",
    url="https://gitlab.com/biolds1/sosse",
    scripts=['sosse-admin'],
    project_urls={
        "Bug Tracker": "https://gitlab.com/biolds1/sosse/-/issues",
        # "Documentation": "https://docs.example.com/HelloWorld/",
        "Source Code": "https://gitlab.com/biolds1/sosse",
    },
    classifiers=[
        "License :: OSI Approved :: GNU Affero General Public License v3"
    ]
)
