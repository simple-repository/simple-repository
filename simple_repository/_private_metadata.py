import typing

from ._frozen_json import FrozenJSONType, JSONMapping
from ._typing_compat import override


class PrivateMetadataMapping(JSONMapping):
    @override
    def _finalize_data(
        self,
        data: typing.Mapping[str, FrozenJSONType],
    ) -> typing.Mapping[str, FrozenJSONType]:
        data = super()._finalize_data(data)
        invalid_keys = ", ".join(
            sorted(repr(key) for key in data if not key.startswith("_")),
        )
        if invalid_keys:
            raise ValueError(
                f"The following keys are invalid for private metadata: {invalid_keys}",
            )
        return data
