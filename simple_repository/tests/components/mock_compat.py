import sys

if sys.version_info >= (3, 8):
    from unittest.mock import AsyncMock
else:
    from mock import AsyncMock

__all__ = ['AsyncMock']
