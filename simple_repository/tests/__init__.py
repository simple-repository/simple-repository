# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import dataclasses
from unittest import mock

from simple_repository import model
from simple_repository.components.core import SimpleRepository


@dataclasses.dataclass(frozen=True)
class MockedFile(model.File):
    # A file which is suitable for using in tests who aren't concerned
    # with File.open, as we mock out the originating repository.
    originating_repository: SimpleRepository = mock.Mock(spec=SimpleRepository)
