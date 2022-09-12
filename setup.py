from setuptools import setup, find_namespace_packages
from os import path, listdir

setup(
    name='OSSE',
    version='0.1',
    packages=find_namespace_packages(include=['se', 'se.*', 'osse', 'osse.*']),

    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=['uwsgi', 'django', 'requests', 'psycopg2', 'django-uwsgi', 'langdetect', 'pygal', 'magic', 'defusedxml', 'selenium'],
    include_package_data=True,

    # metadata to display on PyPI
    author="Laurent Defert",
    author_email="laurent_defert@yahoo.fr",
    description="Open Source Search Engine",
    keywords="search engine",
    url="https://github.com/biolds/osse",
    #project_urls={
    #    "Bug Tracker": "https://bugs.example.com/HelloWorld/",
    #    "Documentation": "https://docs.example.com/HelloWorld/",
    #    "Source Code": "https://code.example.com/HelloWorld/",
    #},
    classifiers=[
        "License :: OSI Approved :: GNU Affero General Public License v3"
    ]
)
