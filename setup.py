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
    description="Open Source Search Engine",
    keywords="search engine",
    url="https://github.com/biolds/sosse",
    scripts=['sosse-admin'],
    #project_urls={
    #    "Bug Tracker": "https://bugs.example.com/HelloWorld/",
    #    "Documentation": "https://docs.example.com/HelloWorld/",
    #    "Source Code": "https://code.example.com/HelloWorld/",
    #},
    classifiers=[
        "License :: OSI Approved :: GNU Affero General Public License v3"
    ]
)
