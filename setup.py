# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from setuptools import find_packages, setup

setup(
    name="simple-repository",
    long_description_content_type="text/markdown",
    author="BE-CSS-SET, CERN",
    url="",
    packages=find_packages(),
    python_requires="~=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Framework :: FastAPI",
        "Operating System :: OS Independent",
        "Typing :: Typed",
    ],
    install_requires=[
        "aiohttp",
        "fastapi>=0.93.0,<0.100.0",
        "packaging",
        "uvicorn[standard]",
    ],
    extras_require={
        "dev": [
            "pre-commit",
        ],
    },
    entry_points={
        'console_scripts': [
            'simple-repository = simple_repository.cli:main',
        ],
    },
)
