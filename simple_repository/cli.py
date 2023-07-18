# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import argparse
from contextlib import asynccontextmanager
import logging
from pathlib import Path
import sqlite3
import typing
from urllib.parse import urlparse

import aiohttp
import fastapi
from fastapi import FastAPI
import uvicorn

from .routers import simple
from .simple.repositories.core import SimpleRepository
from .simple.repositories.http import HttpRepository
from .simple.repositories.local import LocalRepository
from .simple.repositories.metadata_injector import MetadataInjectorRepository
from .simple.repositories.priority_selected import PrioritySelectedProjectsRepository


def is_url(url: str) -> bool:
    return urlparse(url).scheme in ("http", "https")


def configure_parser(parser: argparse.ArgumentParser) -> None:
    parser.description = "Run a Python Package Index"

    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("repository_url", metavar="repository-url", type=str, nargs="+")


def create_repository(
    repository_urls: list[str],
    session: aiohttp.ClientSession,
    database: sqlite3.Connection,
) -> SimpleRepository:
    base_repos: list[SimpleRepository] = []
    repo: SimpleRepository
    for repo_url in repository_urls:
        if is_url(repo_url):
            repo = HttpRepository(
                url=repo_url,
                session=session,
            )
        else:
            repo = LocalRepository(
                index_path=Path(repo_url),
            )
        base_repos.append(repo)

    if len(base_repos) > 1:
        repo = PrioritySelectedProjectsRepository(base_repos)
    else:
        repo = base_repos[0]
    return MetadataInjectorRepository(repo, database, session)


def create_app(repository_urls: list[str]) -> fastapi.FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> typing.AsyncIterator[None]:
        async with aiohttp.ClientSession() as session:
            # Normally we store derived data in a database on disk, but we can
            # equally simply use an in-memory db for simple in-process caching
            with sqlite3.connect(":memory:") as database:
                repo = create_repository(repository_urls, session, database)
                app.include_router(simple.build_router(repo), prefix="")
                yield

    app = FastAPI(
        openapi_url=None,  # Disables automatic OpenAPI documentation (Swagger & Redoc)
        lifespan=lifespan,
    )
    return app


def handler(args: argparse.Namespace) -> None:
    port: int = args.port
    repository_urls: list[str] = args.repository_url
    uvicorn.run(
        app=create_app(repository_urls),
        port=port,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    configure_parser(parser)
    args = parser.parse_args()
    handler(args)
