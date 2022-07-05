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

import os
import zipfile

import pytest

from substra.sdk import exceptions
from substra.sdk import schemas
from substra.sdk import utils


def _unzip(fp, destination):
    with zipfile.ZipFile(fp, "r") as zipf:
        zipf.extractall(destination)


def test_zip_folder(tmp_path):
    # initialise dir to zip
    dir_to_zip = tmp_path / "dir"
    dir_to_zip.mkdir()

    file_items = [
        ("name0.txt", "content0"),
        ("dir1/name1.txt", "content1"),
        ("dir2/name2.txt", "content2"),
    ]

    for name, content in file_items:
        path = dir_to_zip / name
        path.parents[0].mkdir(exist_ok=True)
        path.write_text(content)

    for name, _ in file_items:
        path = dir_to_zip / name
        assert os.path.exists(str(path))

    # zip dir
    fp = utils.zip_folder_in_memory(str(dir_to_zip))
    assert fp

    # unzip dir
    destination_dir = tmp_path / "destination"
    destination_dir.mkdir()
    _unzip(fp, str(destination_dir))
    for name, content in file_items:
        path = destination_dir / name
        assert os.path.exists(str(path))
        assert path.read_text() == content


@pytest.mark.parametrize(
    "filters,expected,exception",
    [
        ("str", None, exceptions.FilterFormatError),
        ({}, None, exceptions.FilterFormatError),
        (
            [{"key": "foo", "type": "bar", "value": "baz"}],
            None,
            exceptions.FilterFormatError,
        ),
        ([{"key": "foo", "type": "is", "value": "baz"}, {}], None, exceptions.FilterFormatError),
        ([{"key": "foo", "type": "is", "value": "baz"}], None, None),
    ],
)
def test_check_metadata_search_filter(filters, expected, exception):
    if exception:
        with pytest.raises(exception):
            utils._check_metadata_search_filters(filters)
    else:
        assert utils._check_metadata_search_filters(filters) == expected


@pytest.mark.parametrize(
    "asset_type,filters,expected,exception",
    [
        (schemas.Type.ComputePlan, {"status": "doing"}, {"status": "PLAN_STATUS_DOING"}, None),
        (schemas.Type.Traintuple, {"status": "done"}, {"status": "STATUS_DONE"}, None),
        (schemas.Type.Traintuple, {"rank": [1]}, {"rank": ["1"]}, None),
        (schemas.Type.DataSample, ["wrong filter type"], None, exceptions.FilterFormatError),
        (schemas.Type.ComputePlan, {"name": ["list"]}, None, exceptions.FilterFormatError),
        (schemas.Type.Traintuple, {"foo": "not allowed key"}, None, exceptions.NotAllowedFilterError),
        (
            schemas.Type.ComputePlan,
            {"name": "cp1", "key": ["key1", "key2"]},
            {"name": "cp1", "key": ["key1", "key2"]},
            None,
        ),
    ],
)
def test_check_and_format_search_filters(asset_type, filters, expected, exception):
    if exception:
        with pytest.raises(exception):
            utils.check_and_format_search_filters(asset_type, filters)
    else:
        assert utils.check_and_format_search_filters(asset_type, filters) == expected


@pytest.mark.parametrize(
    "ordering, exception",
    [
        ("creation_date", None),
        ("start_date", None),
        ("foo", exceptions.OrderingFormatError),
        (None, None),
    ],
)
def test_check_search_ordering(ordering, exception):
    if exception:
        with pytest.raises(exception):
            utils.check_search_ordering(ordering)
    else:
        utils.check_search_ordering(ordering)
