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

import abc
import contextlib
import enum
import json
import pathlib
import typing
import uuid
from typing import Dict
from typing import List
from typing import Optional

import pydantic

from substra.sdk import utils

# TODO create a sub-package schemas:
# types
# inputs
# outputs


_SERVER_NAMES = {
    "dataset": "data_manager",
}


ALGO_INPUT_IDENTIFIER_OPENER = "opener"
ALGO_INPUT_IDENTIFIER_DATASAMPLES = "datasamples"

ALGO_INPUTS_PER_CATEGORY = {
    "ALGO_SIMPLE": {
        ALGO_INPUT_IDENTIFIER_DATASAMPLES: {"kind": "ASSET_DATA_SAMPLE", "multiple": True, "optional": False},
        "model": {"kind": "ASSET_MODEL", "multiple": True, "optional": True},
        ALGO_INPUT_IDENTIFIER_OPENER: {"kind": "ASSET_DATA_MANAGER", "multiple": False, "optional": False},
    },
    "ALGO_AGGREGATE": {
        "model": {"kind": "ASSET_MODEL", "multiple": True, "optional": False},
    },
    "ALGO_COMPOSITE": {
        ALGO_INPUT_IDENTIFIER_DATASAMPLES: {"kind": "ASSET_DATA_SAMPLE", "multiple": True, "optional": False},
        "local": {"kind": "ASSET_MODEL", "multiple": False, "optional": True},
        ALGO_INPUT_IDENTIFIER_OPENER: {"kind": "ASSET_DATA_MANAGER", "multiple": False, "optional": False},
        "shared": {"kind": "ASSET_MODEL", "multiple": False, "optional": True},
    },
    "ALGO_METRIC": {
        ALGO_INPUT_IDENTIFIER_DATASAMPLES: {"kind": "ASSET_DATA_SAMPLE", "multiple": True, "optional": False},
        ALGO_INPUT_IDENTIFIER_OPENER: {"kind": "ASSET_DATA_MANAGER", "multiple": False, "optional": False},
        "predictions": {"kind": "ASSET_MODEL", "multiple": False, "optional": False},
    },
    "ALGO_PREDICT": {
        ALGO_INPUT_IDENTIFIER_DATASAMPLES: {"kind": "ASSET_DATA_SAMPLE", "multiple": True, "optional": False},
        ALGO_INPUT_IDENTIFIER_OPENER: {"kind": "ASSET_DATA_MANAGER", "multiple": False, "optional": False},
        "model": {"kind": "ASSET_MODEL", "multiple": False, "optional": False},
        "shared": {"kind": "ASSET_MODEL", "multiple": False, "optional": True},
    },
}

ALGO_OUTPUTS_PER_CATEGORY = {
    "ALGO_SIMPLE": {
        "model": {"kind": "ASSET_MODEL", "multiple": False},
    },
    "ALGO_AGGREGATE": {
        "model": {"kind": "ASSET_MODEL", "multiple": False},
    },
    "ALGO_COMPOSITE": {
        "local": {"kind": "ASSET_MODEL", "multiple": False},
        "shared": {"kind": "ASSET_MODEL", "multiple": False},
    },
    "ALGO_METRIC": {
        "performance": {"kind": "ASSET_PERFORMANCE", "multiple": False},
    },
    "ALGO_PREDICT": {"predictions": {"kind": "ASSET_MODEL", "multiple": False}},
}


class Type(enum.Enum):
    Algo = "algo"
    DataSample = "data_sample"
    Dataset = "dataset"
    Model = "model"
    Predicttuple = "predicttuple"
    Testtuple = "testtuple"
    Traintuple = "traintuple"
    Aggregatetuple = "aggregatetuple"
    CompositeTraintuple = "composite_traintuple"
    ComputePlan = "compute_plan"
    Organization = "organization"

    def to_server(self):
        """Returns the name used to identify the asset on the backend."""
        name = self.value
        return _SERVER_NAMES.get(name, name)

    def __str__(self):
        return self.name


class AlgoCategory(str, enum.Enum):
    """Algo category"""

    unknown = "ALGO_UNKNOWN"
    simple = "ALGO_SIMPLE"
    composite = "ALGO_COMPOSITE"
    aggregate = "ALGO_AGGREGATE"
    metric = "ALGO_METRIC"
    predict = "ALGO_PREDICT"


class TaskCategory(str, enum.Enum):
    """Task category"""

    unknown = "TASK_UNKNOWN"
    train = "TASK_TRAIN"
    aggregate = "TASK_AGGREGATE"
    composite = "TASK_COMPOSITE"
    predict = "TASK_PREDICT"
    test = "TASK_TEST"


class _PydanticConfig(pydantic.BaseModel):
    """Shared configuration for all schemas here"""

    class Config:
        # Ignore extra fields, leave them unexposed
        extra = "ignore"


class _Spec(_PydanticConfig, abc.ABC):
    """Asset creation specification base class."""

    # pretty print
    def __str__(self):
        return self.json(indent=4)

    def __repr__(self):
        return self.json(indent=4)

    class Meta:
        file_attributes = None

    def is_many(self):
        return False

    @contextlib.contextmanager
    def build_request_kwargs(self):
        # TODO should be located in the backends/remote module
        # Serialize and deserialize to prevent errors eg with pathlib.Path
        data = json.loads(self.json(exclude_unset=True))
        if self.Meta.file_attributes:
            with utils.extract_files(data, self.Meta.file_attributes) as (data, files):
                yield (data, files)
        else:
            yield data, None

    @staticmethod
    def compute_key() -> str:
        return str(uuid.uuid4())


class Permissions(_PydanticConfig):
    """Specification for permissions. If public is False,
    give the list of authorized ids.
    """

    public: bool
    authorized_ids: typing.List[str]  # List of authorized organization ids if private


class PrivatePermissions(_PydanticConfig):
    """Specification for private permissions. Only the organizations whose
    ids are in authorized_ids can access the asset.
    """

    authorized_ids: typing.List[str]  # List of authorized organization ids


class DataSampleSpec(_Spec):
    """Specification to create one or many data samples
    To create one data sample, use the 'path' field, otherwise use
    the 'paths' field.
    """

    path: Optional[pathlib.Path]  # Path to the data sample if only one
    paths: Optional[List[pathlib.Path]]  # Path to the data samples if several
    test_only: bool  # If the data sample is for train or test
    data_manager_keys: typing.List[str]

    type_: typing.ClassVar[Type] = Type.DataSample

    def is_many(self):
        return self.paths and len(self.paths) > 0

    @pydantic.root_validator(pre=True)
    def exclusive_paths(cls, values):  # noqa: N805
        """Check that one and only one path(s) field is defined."""
        if "paths" in values and "path" in values:
            raise ValueError("'path' and 'paths' fields are exclusive.")
        if "paths" not in values and "path" not in values:
            raise ValueError("'path' or 'paths' field must be set.")
        return values

    @contextlib.contextmanager
    def build_request_kwargs(self, local):
        # redefine kwargs builder to handle the local paths
        # Serialize and deserialize to prevent errors eg with pathlib.Path
        data = json.loads(self.json(exclude_unset=True))
        if local:
            with utils.extract_data_sample_files(data) as (data, files):
                yield (data, files)
        else:
            yield data, None


def check_asset_key_or_parent_ref(cls, values):
    """Check that either (asset key) or (parent_task_key, parent_task_output_identifier) are set, but not both."""

    has_asset_key = bool(values.get("asset_key"))
    has_parent = bool(values.get("parent_task_key")) and bool(values.get("parent_task_output_identifier"))

    if has_asset_key != has_parent:  # xor
        return values

    raise ValueError("either asset_key or both (parent_task_key, parent_task_output_identifier) must be provided")


class InputRef(_PydanticConfig):
    """Specification of a compute task input"""

    identifier: str
    asset_key: Optional[str]
    parent_task_key: Optional[str]
    parent_task_output_identifier: Optional[str]

    # either (asset_key) or (parent_task_key, parent_task_output_identifier) must be specified
    _check_asset_key_or_parent_ref = pydantic.root_validator(allow_reuse=True)(check_asset_key_or_parent_ref)


class ComputeTaskOutput(_PydanticConfig):
    permissions: Permissions
    # "is_transient" will be added here


class _ComputePlanComputeTaskSpec(_Spec):
    """Specification of a compute task inside a compute plan specification"""

    algo_key: str
    tag: Optional[str]
    metadata: Optional[Dict[str, str]]
    inputs: Optional[List[InputRef]]
    outputs: Optional[Dict[str, ComputeTaskOutput]]


class ComputePlanTraintupleSpec(_ComputePlanComputeTaskSpec):
    """Specification of a traintuple inside a compute
    plan specification"""

    data_manager_key: str
    train_data_sample_keys: List[str]
    traintuple_id: str
    in_models_ids: Optional[List[str]]


class ComputePlanAggregatetupleSpec(_ComputePlanComputeTaskSpec):
    """Specification of an aggregate tuple inside a compute
    plan specification"""

    aggregatetuple_id: str
    worker: str
    in_models_ids: Optional[List[str]]


class ComputePlanCompositeTraintupleSpec(_ComputePlanComputeTaskSpec):
    """Specification of a composite traintuple inside a compute
    plan specification"""

    composite_traintuple_id: str
    data_manager_key: str
    train_data_sample_keys: List[str]
    in_head_model_id: Optional[str]
    in_trunk_model_id: Optional[str]


class ComputePlanPredicttupleSpec(_ComputePlanComputeTaskSpec):
    """Specification of a predict tuple inside a compute
    plan specification"""

    predicttuple_id: str
    traintuple_id: str
    data_manager_key: str
    test_data_sample_keys: List[str]


class ComputePlanTesttupleSpec(_ComputePlanComputeTaskSpec):
    """Specification of a testtuple inside a compute
    plan specification"""

    predicttuple_id: str
    data_manager_key: str
    test_data_sample_keys: List[str]


class _BaseComputePlanSpec(_Spec, abc.ABC):
    key: str
    traintuples: Optional[List[ComputePlanTraintupleSpec]]
    composite_traintuples: Optional[List[ComputePlanCompositeTraintupleSpec]]
    aggregatetuples: Optional[List[ComputePlanAggregatetupleSpec]]
    predicttuples: Optional[List[ComputePlanPredicttupleSpec]]
    testtuples: Optional[List[ComputePlanTesttupleSpec]]


class ComputePlanSpec(_BaseComputePlanSpec):
    """Specification for creating a compute plan"""

    key: str = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    tag: Optional[str]
    name: str
    clean_models: Optional[bool]
    metadata: Optional[Dict[str, str]]

    type_: typing.ClassVar[Type] = Type.ComputePlan

    @contextlib.contextmanager
    def build_request_kwargs(self):
        # default values are not dumped when `exclude_unset` flag is enabled,
        # this is why we need to reimplement this custom function.
        data = json.loads(self.json(exclude_unset=True))
        data["key"] = self.key
        yield data, None


class UpdateComputePlanSpec(_BaseComputePlanSpec):
    """Specification for updating a compute plan"""

    pass


class AlgoInputSpec(_Spec):
    identifier: str
    multiple: bool
    optional: bool
    kind: str


class AlgoOutputSpec(_Spec):
    identifier: str
    multiple: bool
    kind: str


class DatasetSpec(_Spec):
    """Specification for creating a dataset"""

    name: str
    data_opener: pathlib.Path  # Path to the data opener
    type: str
    description: pathlib.Path  # Path to the description file
    permissions: Permissions
    metadata: Optional[Dict[str, str]]
    logs_permission: Permissions

    type_: typing.ClassVar[Type] = Type.Dataset

    class Meta:
        file_attributes = (
            "data_opener",
            "description",
        )


class AlgoSpec(_Spec):
    """Specification for creating an algo"""

    name: str
    description: pathlib.Path
    file: pathlib.Path
    permissions: Permissions
    metadata: Optional[Dict[str, str]]
    category: AlgoCategory

    inputs: Optional[List[AlgoInputSpec]] = None
    outputs: Optional[List[AlgoOutputSpec]] = None

    @pydantic.validator("inputs", pre=True, always=True)
    def validate_inputs(cls, inputs, values):  # noqa: N805
        if inputs is None:
            inputs = [
                AlgoInputSpec(
                    identifier=identifier,
                    kind=algo_input["kind"],
                    optional=algo_input["optional"],
                    multiple=algo_input["multiple"],
                )
                for identifier, algo_input in ALGO_INPUTS_PER_CATEGORY[values["category"]].items()
            ]

        return inputs

    @pydantic.validator("outputs", pre=True, always=True)
    def validate_outputs(cls, outputs, values):  # noqa: N805
        if outputs is None:
            outputs = [
                AlgoOutputSpec(
                    identifier=identifier,
                    kind=algo_input["kind"],
                    multiple=algo_input["multiple"],
                )
                for identifier, algo_input in ALGO_OUTPUTS_PER_CATEGORY[values["category"]].items()
            ]

        return outputs

    type_: typing.ClassVar[Type] = Type.Algo

    @contextlib.contextmanager
    def build_request_kwargs(self):
        # TODO should be located in the backends/remote module
        # Serialize and deserialize to prevent errors eg with pathlib.Path
        data = json.loads(self.json(exclude_unset=True))

        # Waiting for algo inputs/outputs to be added by the public API,
        # these data are added on the fly to the request, without being exposed to the user.
        # Computed fields using `@property` are not dumped when `exclude_unset` flag is enabled,
        # this is why we need to reimplement this custom function.
        data["inputs"] = ALGO_INPUTS_PER_CATEGORY[self.category]
        data["outputs"] = ALGO_OUTPUTS_PER_CATEGORY[self.category]

        if self.Meta.file_attributes:
            with utils.extract_files(data, self.Meta.file_attributes) as (data, files):
                yield (data, files)
        else:
            yield data, None

    class Meta:
        file_attributes = (
            "file",
            "description",
        )


class _TupleSpec(_Spec):
    key: str = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    tag: Optional[str]
    compute_plan_key: Optional[str]
    metadata: Optional[Dict[str, str]]
    algo_key: str
    inputs: Optional[List[InputRef]]
    outputs: Optional[Dict[str, ComputeTaskOutput]]

    @contextlib.contextmanager
    def build_request_kwargs(self):
        # default values are not dumped when `exclude_unset` flag is enabled,
        # this is why we need to reimplement this custom function.
        data = json.loads(self.json(exclude_unset=True))
        data["key"] = self.key
        data["category"] = self.category
        data["inputs"] = [input.dict() for input in self.inputs] if self.inputs else []
        data["outputs"] = {k: v.dict() for k, v in self.outputs.items()} if self.outputs else {}
        yield data, None


class TraintupleSpec(_TupleSpec):
    """Specification for creating a traintuple"""

    data_manager_key: str
    train_data_sample_keys: List[str]
    in_models_keys: Optional[List[str]]
    rank: Optional[int]  # Rank of the traintuple in the compute plan
    category: TaskCategory = pydantic.Field(TaskCategory.train, const=True)

    compute_plan_attr_name: typing.ClassVar[str] = "traintuple_keys"
    type_: typing.ClassVar[Type] = Type.Traintuple

    @classmethod
    def from_compute_plan(cls, compute_plan_key: str, rank: int, spec: ComputePlanTraintupleSpec) -> "TraintupleSpec":
        return TraintupleSpec(
            key=spec.traintuple_id,
            algo_key=spec.algo_key,
            data_manager_key=spec.data_manager_key,
            train_data_sample_keys=spec.train_data_sample_keys,
            in_models_keys=spec.in_models_ids or list(),
            inputs=spec.inputs,
            outputs=spec.outputs,
            tag=spec.tag,
            compute_plan_key=compute_plan_key,
            rank=rank,
            metadata=spec.metadata,
        )


class AggregatetupleSpec(_TupleSpec):
    """Specification for creating an aggregate tuple"""

    worker: str
    in_models_keys: List[str]
    rank: Optional[int]
    category: TaskCategory = pydantic.Field(TaskCategory.aggregate, const=True)

    compute_plan_attr_name: typing.ClassVar[str] = "aggregatetuple_keys"
    type_: typing.ClassVar[Type] = Type.Aggregatetuple

    @classmethod
    def from_compute_plan(
        cls, compute_plan_key: str, rank: int, spec: ComputePlanAggregatetupleSpec
    ) -> "AggregatetupleSpec":
        return AggregatetupleSpec(
            key=spec.aggregatetuple_id,
            algo_key=spec.algo_key,
            worker=spec.worker,
            in_models_keys=spec.in_models_ids or list(),
            inputs=spec.inputs,
            outputs=spec.outputs,
            tag=spec.tag,
            compute_plan_key=compute_plan_key,
            rank=rank,
            metadata=spec.metadata,
        )


class CompositeTraintupleSpec(_TupleSpec):
    """Specification for creating a composite traintuple"""

    data_manager_key: str
    train_data_sample_keys: List[str]
    in_head_model_key: Optional[str]
    in_trunk_model_key: Optional[str]
    rank: Optional[int]
    category: TaskCategory = pydantic.Field(TaskCategory.composite, const=True)

    compute_plan_attr_name: typing.ClassVar[str] = "composite_traintuple_keys"
    type_: typing.ClassVar[Type] = Type.CompositeTraintuple

    @classmethod
    def from_compute_plan(
        cls, compute_plan_key: str, rank: int, spec: ComputePlanCompositeTraintupleSpec
    ) -> "CompositeTraintupleSpec":
        return CompositeTraintupleSpec(
            key=spec.composite_traintuple_id,
            algo_key=spec.algo_key,
            data_manager_key=spec.data_manager_key,
            train_data_sample_keys=spec.train_data_sample_keys,
            in_head_model_key=spec.in_head_model_id,
            in_trunk_model_key=spec.in_trunk_model_id,
            inputs=spec.inputs,
            outputs=spec.outputs,
            tag=spec.tag,
            compute_plan_key=compute_plan_key,
            rank=rank,
            metadata=spec.metadata,
        )


class PredicttupleSpec(_TupleSpec):
    """Specification for creating a predict tuple"""

    traintuple_key: str
    data_manager_key: str
    test_data_sample_keys: List[str]
    category: TaskCategory = pydantic.Field(TaskCategory.predict, const=True)

    compute_plan_attr_name: typing.ClassVar[str] = "predicttuple_keys"
    type_: typing.ClassVar[Type] = Type.Predicttuple

    @classmethod
    def from_compute_plan(cls, compute_plan_key: str, spec: ComputePlanPredicttupleSpec) -> "PredicttupleSpec":
        return PredicttupleSpec(
            key=spec.predicttuple_id,
            algo_key=spec.algo_key,
            traintuple_key=spec.traintuple_id,
            inputs=spec.inputs,
            outputs=spec.outputs,
            tag=spec.tag,
            data_manager_key=spec.data_manager_key,
            test_data_sample_keys=spec.test_data_sample_keys,
            compute_plan_key=compute_plan_key,
            metadata=spec.metadata,
        )


class TesttupleSpec(_TupleSpec):
    """Specification for creating a testtuple"""

    predicttuple_key: str
    data_manager_key: str
    test_data_sample_keys: List[str]
    category: TaskCategory = pydantic.Field(TaskCategory.test, const=True)

    type_: typing.ClassVar[Type] = Type.Testtuple

    @classmethod
    def from_compute_plan(cls, compute_plan_key: str, spec: ComputePlanTesttupleSpec) -> "TesttupleSpec":
        return TesttupleSpec(
            algo_key=spec.algo_key,
            predicttuple_key=spec.predicttuple_id,
            inputs=spec.inputs,
            outputs=spec.outputs,
            tag=spec.tag,
            data_manager_key=spec.data_manager_key,
            test_data_sample_keys=spec.test_data_sample_keys,
            compute_plan_key=compute_plan_key,
            metadata=spec.metadata,
        )
