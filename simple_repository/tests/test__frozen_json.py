import re
import textwrap

import pytest

from simple_repository import _frozen_json


@pytest.fixture
def simple_json() -> _frozen_json.JSONMapping:
    return _frozen_json.JSONMapping(
        (
            ("string", "hello world 😀"),
            ("int", 1),
            ("bool", True),
            ("float", 3.14),
            ("null", None),
            ("tuple", (1, True, 3.14, None)),
            (
                "mapping",
                _frozen_json.JSONMapping(
                    (("int", 1), ("bool", True), ("float", 3.14), ("null", None)),
                ),
            ),
        ),
    )


def test_frozen_json_mapping__str(simple_json: _frozen_json.JSONMapping):
    assert simple_json["string"] == "hello world 😀"
    assert isinstance(simple_json["string"], str)


def test_frozen_json_mapping__int(simple_json: _frozen_json.JSONMapping):
    assert simple_json["int"] == 1
    assert isinstance(simple_json["int"], int)


def test_frozen_json_mapping__bool(simple_json: _frozen_json.JSONMapping):
    assert simple_json["bool"] is True


def test_frozen_json_mapping__float(simple_json: _frozen_json.JSONMapping):
    assert simple_json["float"] == 3.14
    assert isinstance(simple_json["float"], float)


def test_frozen_json_mapping__null(simple_json: _frozen_json.JSONMapping):
    assert simple_json["null"] is None


def test_frozen_json_mapping__tuple(simple_json: _frozen_json.JSONMapping):
    assert isinstance(simple_json["tuple"], tuple)


def test_frozen_json_mapping__mapping(simple_json: _frozen_json.JSONMapping):
    assert isinstance(simple_json["mapping"], _frozen_json.JSONMapping)
    assert list(simple_json["mapping"].keys()) == ["int", "bool", "float", "null"]


def test_frozen_json_mapping__init__with_none():
    m = _frozen_json.JSONMapping()
    assert tuple(m.items()) == ()


def test_frozen_json_mapping__from_any_mapping__with__list():
    m = _frozen_json.JSONMapping.from_any_mapping({"a": [1, 2, 3]})
    assert isinstance(m["a"], tuple)
    assert m["a"] == (1, 2, 3)


def test_frozen_json_mapping__from_any_mapping__with_dict():
    m = _frozen_json.JSONMapping.from_any_mapping({"a": {"b": [4, 5, None]}})
    assert isinstance(m["a"], _frozen_json.JSONMapping)
    assert isinstance(m["a"]["b"], tuple)
    assert m["a"]["b"] == (4, 5, None)


def test_frozen_json_mapping__init__from_any_mapping__with__dict_inside_tuple():
    m = _frozen_json.JSONMapping.from_any_mapping({"a": (1, 2, {})})
    assert isinstance(m["a"][2], _frozen_json.JSONMapping)


def test_frozen_json_mapping__init__from_any_mapping__with__circular_dict():
    data = {}
    data["data"] = data
    with pytest.raises(RecursionError):
        # It is not possible to have an immutable type that is recursive.
        _frozen_json.JSONMapping.from_any_mapping({"a": data})


def test_frozen_json_mapping__from_any_mapping__with_invalid_keys():
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Unable to convert non-string key(s) to a valid frozen "
            "JSON type (got '1' (type int))",
        ),
    ):
        _frozen_json.JSONMapping.from_any_mapping({1: 1})  # type: ignore[arg-type]  # intentionally invalid for testing.


def test_frozen_json_mapping__from_any_mapping__with_invalid_type():
    class InvalidType:
        pass

    with pytest.raises(
        ValueError,
        match="Unable to convert type InvalidType to a valid frozen JSON type",
    ):
        _frozen_json.JSONMapping.from_any_mapping({"a": InvalidType()})


def test_frozen_json_mapping____str__(simple_json: _frozen_json.JSONMapping):
    assert (
        str(simple_json)
        == textwrap.dedent("""
    JSONMapping((('string', 'hello world 😀'), ('int', 1), ('bool', True), ('float', 3.14), ('null', None), ('tuple', (1, True, 3.14, None)), ('mapping', JSONMapping((('int', 1), ('bool', True), ('float', 3.14), ('null', None))))))
    """).strip()
    )


def test_frozen_json_mapping____repr__(simple_json: _frozen_json.JSONMapping):
    assert (
        repr(simple_json)
        == textwrap.dedent("""
    JSONMapping((('string', 'hello world 😀'), ('int', 1), ('bool', True), ('float', 3.14), ('null', None), ('tuple', (1, True, 3.14, None)), ('mapping', JSONMapping((('int', 1), ('bool', True), ('float', 3.14), ('null', None))))))
    """).strip()
    )


def test_frozen_json_mapping____hash__(simple_json: _frozen_json.JSONMapping):
    assert isinstance(hash(simple_json), int)


def test_frozen_json_mapping____hash___consistency():
    # Validate that the same object, produced at different times, produces the same hash.
    a = hash(_frozen_json.JSONMapping.from_any_mapping({"a": [1, 2, 3, {}]}))
    b = hash(_frozen_json.JSONMapping.from_any_mapping({"a": [1, 2, 3, {}]}))
    assert a == b


def test_frozen_json_mapping__or_operator(simple_json: _frozen_json.JSONMapping):
    new = simple_json | {"int": 2}
    assert new["int"] == 2
    assert simple_json["int"] == 1


def test_frozen_json_mapping__or_operator__ensure_frozen_too(
    simple_json: _frozen_json.JSONMapping,
):
    new = simple_json | {"some": {"mutable": ["things"]}}
    assert isinstance(new["some"], _frozen_json.JSONMapping)
    assert isinstance(new["some"]["mutable"], tuple)
    assert new["some"] == {"mutable": ("things",)}


def test_frozen_json_mapping__drop(simple_json: _frozen_json.JSONMapping):
    new = _frozen_json.JSONMapping(
        {key: value for key, value in simple_json.items() if key not in ["int"]},
    )
    assert simple_json["int"] == 1
    print("N:", new)
    with pytest.raises(KeyError):
        _ = new["int"]


def test_frozen_json_mapping__eq(simple_json: _frozen_json.JSONMapping):
    # __eq__ is given to us by the Mapping protocol, but quickly validate that it behaves as we expect
    # (https://docs.python.org/3/library/collections.abc.html#collections-abstract-base-classes)
    obj1 = _frozen_json.JSONMapping((("a", 1),))
    obj2 = _frozen_json.JSONMapping((("a", 1),))
    obj3 = _frozen_json.JSONMapping((("a", 2),))
    obj4 = _frozen_json.JSONMapping((("a", 1), ("b", 2)))

    assert obj1 == obj2
    assert obj1 != obj3
    assert obj1 != obj4
