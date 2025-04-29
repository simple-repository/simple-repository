from __future__ import annotations

from collections.abc import Mapping
import typing

FrozenJSONType: typing.TypeAlias = typing.Union[
    int,
    float,
    bool,
    None,
    typing.Tuple["FrozenJSONType", ...],
    "JSONMapping",
]


class JSONMapping(typing.Mapping[str, FrozenJSONType]):
    """
    A frozen JSON mapping.

    Note: JSONMapping is hashable (possible since it is frozen).

    Note:

        The JSONMapping type supports the dict union interface, meaning that you can update
        specific keys in the mapping (into a new instance) with:

            new_mapping = mapping | {'some-new-value': 's'}

        Removing a key is done with:

            new_mapping = mapping.drop('some-new-value')

    Note that this class also supports `__contains__`, `keys`, `items`, `values`, `get` and
    `__eq__`.

    """

    def __init__(
        self,
        items: typing.Tuple[
            typing.Tuple[str, FrozenJSONType],
            ...,
        ]
        | typing.Mapping[str, FrozenJSONType]
        | None = None,
    ):
        self._data: typing.Mapping[str, FrozenJSONType] = self._finalize_data(
            dict(items or ()),
        )

    def _finalize_data(
        self,
        data: typing.Mapping[str, FrozenJSONType],
    ) -> typing.Mapping[str, FrozenJSONType]:
        """
        A hook to allow subclasses to refine the internal data. This could be used for validation or
        default generation, for example.
        """
        return data

    @classmethod
    def from_any_dict(
        cls,
        data: typing.Mapping[str, typing.Any],
        sub_dict_cls: typing.Optional[typing.Type[JSONMapping]] = None,
    ) -> typing.Self:
        """
        Recursively transform the given data in to compatible types for JSONMapping.

        """
        if sub_dict_cls is None:
            sub_dict_cls_t: typing.Type[JSONMapping] = JSONMapping
        else:
            sub_dict_cls_t = sub_dict_cls

        @typing.overload
        def transform(value: typing.Mapping[str, typing.Any]) -> JSONMapping: ...

        @typing.overload
        def transform(value: typing.Any) -> FrozenJSONType: ...

        def transform(value: typing.Any) -> FrozenJSONType:
            if isinstance(value, Mapping) and not isinstance(value, JSONMapping):
                non_str_k = ", ".join(
                    sorted(
                        f"{repr(k)!r} (type {type(k).__name__})"
                        for k in value.keys()
                        if not isinstance(k, str)
                    ),
                )
                if non_str_k:
                    raise ValueError(
                        f"Unable to convert non-string key(s) to a valid frozen JSON "
                        f"type (got {non_str_k})",
                    )
                return sub_dict_cls_t(
                    tuple((k, transform(v)) for k, v in value.items()),
                )
            if isinstance(value, (list, tuple)):
                return tuple(transform(v) for v in value)
            if not isinstance(value, valid_types):
                raise ValueError(
                    f"Unable to convert type {type(value).__name__} to a valid frozen JSON type",
                )
            return value

        return cls(transform(data))

    def __getitem__(self, key: str) -> FrozenJSONType:
        return self._data.__getitem__(key)

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({repr(tuple(self._data.items()))})"

    def __or__(self, other: typing.Mapping[str, FrozenJSONType]) -> JSONMapping:
        return type(self)({**self._data, **other})

    def drop(self, *keys: str) -> typing.Self:
        """Remove the given keys from the mapping (in a new instance)"""
        return type(self)({k: v for k, v in self._data.items() if k not in keys})

    def __hash__(self) -> int:
        data_hash = tuple((k, hash(v)) for k, v in self.items())
        return hash(data_hash)


valid_types = (int, float, bool, type(None), tuple, JSONMapping)
