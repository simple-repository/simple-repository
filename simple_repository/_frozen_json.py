from __future__ import annotations

from collections.abc import Mapping
import sys
import typing

from ._typing_compat import TypeAlias

if sys.version_info >= (3, 10):
    from types import NoneType
else:
    NoneType = type(None)

if typing.TYPE_CHECKING:
    from ._typing_compat import Self

FrozenJSONType: TypeAlias = typing.Union[
    str,
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

        You can apply comprehensions indirectly:

            new_mapping = JSONMapping(
                {key: value for key, value in mapping.items() if key not in ['some-new-value']}
            )

    Note that this class also supports `__contains__`, `keys`, `items`, `values`, `get` and
    `__eq__`.

    """

    def __init__(
        self,
        items: typing.Union[
            typing.Tuple[
                typing.Tuple[str, FrozenJSONType],
                ...,
            ],
            typing.Mapping[str, FrozenJSONType],
            None,
        ] = None,
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
    def from_any_mapping(
        cls,
        data: typing.Mapping[str, typing.Any],
        sub_mapping_cls: typing.Optional[typing.Type[JSONMapping]] = None,
    ) -> Self:
        """
        Recursively transform the given data in to compatible types for JSONMapping.

        """
        if sub_mapping_cls is None:
            sub_mapping_cls_t: typing.Type[JSONMapping] = JSONMapping
        else:
            sub_mapping_cls_t = sub_mapping_cls

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
                return sub_mapping_cls_t(
                    tuple((k, transform(v)) for k, v in value.items()),
                )
            if isinstance(value, (list, tuple)):
                return tuple(transform(v) for v in value)
            # For everything else, it must match what is allowed in FrozenJSONType.
            if isinstance(value, (str, int, float, bool, NoneType)):
                return value  # only_py37_type: ignore[return-value]

            raise ValueError(
                f"Unable to convert type {type(value).__name__} to a valid frozen JSON type",
            )

        return cls(transform(data))

    def __getitem__(self, key: str) -> FrozenJSONType:
        return self._data[key]

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({repr(tuple(self._data.items()))})"

    def __or__(self, other: typing.Mapping[str, typing.Any]) -> Self:
        if not isinstance(other, type(self)):
            other = type(self).from_any_mapping(other)
        return type(self)({**self._data, **other})

    def __hash__(self) -> int:
        return hash(tuple(self.items()))
