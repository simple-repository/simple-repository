import asyncio
import typing

import aiohttp


class MockedStreamReader:  # aiohttp.StreamReader
    def __init__(self, chunks: list[bytes] = None):
        self._chunks = chunks or []

    async def iter_chunks(self) -> typing.AsyncGenerator[bytes, None]:
        for chunk in self._chunks:
            yield chunk, False


class MockedClientResponse:  # aiohttp.ClientResponse
    def __init__(self, status: int = 200, text: str = "", chunks: list[bytes] = None):
        self.status = status
        self._text = text
        self._chunks = chunks or []
        self.content = MockedStreamReader(chunks=self._chunks)

    async def text(self) -> str:
        return self._text


class MockedRequestContextManager:  # aiohttp.client._RequestContextManager
    def __init__(self, status: int = 200, text: str = "", chunks: list[bytes] = None):
        self.status = status
        self._text = text
        self._chunks = chunks or []

    async def __aenter__(self):
        return MockedClientResponse(
            status=self.status,
            text=self._text,
            chunks=self._chunks
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockedClientSession():  # aiohttp.ClientSession
    def __init__(self, real_session: aiohttp.ClientSession = None):
        self.real_session = real_session
        self.response_mocks = {}

    def add_mocked_response(
            self,
            url: str,
            status: int = 200,
            text: str = "",
            chunks: list[bytes] = None,
    ) -> None:
        self.response_mocks[url] = {
            "status": status,
            "text": text,
            "chunks": chunks,
        }

    def _request(self, method: typing.Callable, url: str, *args, **kwargs):
        try:
            options = self.response_mocks[url]
        except KeyError:
            if self.real_session:
                return method(self=self.real_session, url=url, *args, **kwargs)
        else:
            return MockedRequestContextManager(
                status=options["status"],
                text=options["text"],
                chunks=options["chunks"],
            )
        raise ValueError(
            f"URL '{url}' not found in the response mocks, "
            "and no real client session has been provided"
        )

    def request(self, url: str, *args, **kwargs) -> MockedRequestContextManager:
        return self._request(aiohttp.ClientSession.request, url, *args, **kwargs)

    def options(self, url: str, *args, **kwargs) -> MockedRequestContextManager:
        return self._request(aiohttp.ClientSession.options, url, *args, **kwargs)

    def get(self, url: str, *args, **kwargs) -> MockedRequestContextManager:
        return self._request(aiohttp.ClientSession.get, url, *args, **kwargs)

    def post(self, url: str, *args, **kwargs) -> MockedRequestContextManager:
        return self._request(aiohttp.ClientSession.post, url, *args, **kwargs)

    def put(self, url: str, *args, **kwargs) -> MockedRequestContextManager:
        return self._request(aiohttp.ClientSession.put, url, *args, **kwargs)

    def patch(self, url: str, *args, **kwargs) -> MockedRequestContextManager:
        return self._request(aiohttp.ClientSession.patch, url, *args, **kwargs)

    def delete(self, url: str, *args, **kwargs) -> MockedRequestContextManager:
        return self._request(aiohttp.ClientSession.delete, url, *args, **kwargs)

    def __getattribute__(self, item: str):
        try:
            return super().__getattribute__(item)
        except AttributeError:
            return self.real_session.__getattribute__(item)

    async def __aenter__(self) -> "MockedClientSession":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
