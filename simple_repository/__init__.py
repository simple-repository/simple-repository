"""
Specialised PEP-503 simple repository components exposed through a standardised
client interface, suitable for re-use in both client and server implementations
"""

from ._version import version as __version__  # noqa
from .components.core import SimpleRepository  # noqa

__all__ = ['__version__', 'SimpleRepository']
