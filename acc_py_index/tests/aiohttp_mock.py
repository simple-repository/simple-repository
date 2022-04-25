from unittest import mock


class MockedRequestContextManager:
    def __init__(self, response_mock: mock.Mock):
        self.response_mock = response_mock

    async def __aenter__(self):
        return self.response_mock

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
