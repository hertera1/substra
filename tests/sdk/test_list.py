# Copyright 2018 Owkin, inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest

from substra.sdk import models
from substra.sdk import schemas

from .. import datastore
from ..utils import make_paginated_response
from ..utils import mock_requests


@pytest.mark.parametrize(
    "asset_name",
    [
        "metric",
        "dataset",
        "algo",
        "testtuple",
        "traintuple",
        "aggregatetuple",
        "composite_traintuple",
        "compute_plan",
    ],
)
def test_list_asset(asset_name, client, mocker):
    item = getattr(datastore, asset_name.upper())
    method = getattr(client, f"list_{asset_name}")

    mocked_response = make_paginated_response([item])
    m = mock_requests(mocker, "get", response=mocked_response)

    response = method()

    schema_type = asset_name

    assert response == [models.SCHEMA_TO_MODEL[schemas.Type(schema_type)](**item)]
    m.assert_called()


def test_list_asset_with_filters_failure(client, mocker):
    items = [datastore.ALGO]
    m = mock_requests(mocker, "get", response=items)

    filters = "foo"
    with pytest.raises(ValueError) as exc_info:
        client.list_algo(filters)

    m.assert_not_called()
    assert str(exc_info.value).startswith("Cannot load filters")
