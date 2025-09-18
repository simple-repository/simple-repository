import pytest

from simple_repository._private_metadata import JSONMapping, PrivateMetadataMapping


def test__empty() -> None:
    assert PrivateMetadataMapping() == {}


def test__valid_names() -> None:
    mapping = PrivateMetadataMapping.from_any_mapping(
        {"_a": 1, "_b": {"not_private": 1}},
    )
    assert list(mapping.keys()) == ["_a", "_b"]
    assert type(mapping["_b"]) is JSONMapping


def test__invalid_names() -> None:
    with pytest.raises(ValueError, match="invalid for private metadata: 'a', 'b'"):
        PrivateMetadataMapping({"_f": 1, "a": 1, "b": True})
