# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

"""
Specialised PEP-503 simple repository components exposed through a standardised
client interface, suitable for reuse in both client and server implementations
"""

from ._version import version as __version__  # noqa
from .components.core import SimpleRepository  # noqa

__all__ = ["__version__", "SimpleRepository"]
