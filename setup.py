"""
setup.py for acc-py-index.

For reference see
https://packaging.python.org/guides/distributing-packages-using-setuptools/
"""
from pathlib import Path

from setuptools import find_packages, setup

HERE = Path(__file__).parent.absolute()
with (HERE / "README.md").open("rt") as fh:
    LONG_DESCRIPTION = fh.read().strip()

REQUIREMENTS: dict[str, list[str]] = {
    "core": [
        "aiohttp",
        "cachetools",
        "fastapi",
        "gunicorn",
        "packaging",
        "uvicorn[standard]",
    ],
    "test": [
        "pytest",
        "pytest_asyncio",
        "httpx",  # httpx is needed for starlette.TestClient. https://www.starlette.io/#dependencies
    ],
    "dev": [
        "pre-commit",
    ],
    "doc": [
        "acc-py-sphinx",
        "sphinx",
    ],
}

setup(
    name="acc-py-index",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Wouter Koorn",
    author_email="wouter.koorn@cern.ch",
    maintainer="Acc-Py team",
    maintainer_email="acc-python-support@cern.ch",
    url="https://gitlab.cern.ch/acc-co/devops/python/package-index/acc-py-index",
    packages=find_packages(),
    package_data={"": ["log_config.json"]},
    python_requires="~=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Framework :: FastAPI",
        "Operating System :: OS Independent",
        "Typing :: Typed",
    ],
    install_requires=REQUIREMENTS["core"],
    extras_require={
        **REQUIREMENTS,
        # The "dev" extra is the union of "test" and "doc", with an option
        # to have explicit development dependencies listed.
        "dev": [
            req
            for extra in ["dev", "test", "doc"]
            for req in REQUIREMENTS.get(extra, [])
        ],
        # The "all" extra is the union of all requirements.
        "all": [req for reqs in REQUIREMENTS.values() for req in reqs],
    },
)
