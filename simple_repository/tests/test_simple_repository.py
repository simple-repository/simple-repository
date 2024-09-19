from __future__ import annotations

import simple_repository


def test_version() -> None:
    assert simple_repository.__version__ != "0.0.0"
