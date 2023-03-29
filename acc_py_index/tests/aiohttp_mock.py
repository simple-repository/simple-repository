import types
from unittest import mock


class MockedRequestContextManager:
    def __init__(self, response_mock: mock.Mock) -> None:
        self.response_mock: mock.Mock = response_mock

    async def __aenter__(self) -> mock.Mock:
        return self.response_mock

    async def __aexit__(
        self,
        exc_type: type,
        exc_val: Exception,
        exc_tb: types.TracebackType,
    ) -> None:
        pass
