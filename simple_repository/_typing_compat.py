import sys

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

if sys.version_info >= (3, 8):
    from typing import Protocol, TypedDict
else:
    from typing_extensions import Protocol, TypedDict

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

__all__ = [
    'override',
    'TypedDict',
    'TypeAlias',
    'Protocol',
]
