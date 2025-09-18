# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import sys
import typing

if typing.TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

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
    "override",
    "Self",
    "TypedDict",
    "TypeAlias",
    "Protocol",
]
