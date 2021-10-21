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

import json
import os
import zipfile

import substra

current_directory = os.path.dirname(__file__)
assets_directory = os.path.join(current_directory, '../assets')

client = substra.Client.from_config_file(profile_name="node-1")

ALGO = {
    'name': 'Constant death predictor',
    'category': 'ALGO_SIMPLE',
    'description': os.path.join(assets_directory, 'algo_constant/description.md'),
    'permissions': {
        'public': False,
        'authorized_ids': []
    },
}
ALGO_DOCKERFILE_FILES = [
    os.path.join(assets_directory, 'algo_constant/algo.py'),
    os.path.join(assets_directory, 'algo_constant/Dockerfile'),
]

########################################################
#       Build archive
########################################################

archive_path = os.path.join(current_directory, 'algo_constant.zip')
with zipfile.ZipFile(archive_path, 'w') as z:
    for filepath in ALGO_DOCKERFILE_FILES:
        z.write(filepath, arcname=os.path.basename(filepath))
ALGO['file'] = archive_path

########################################################
#       Load keys for dataset and metric
########################################################

assets_keys_path = os.path.join(current_directory, '../assets_keys.json')
with open(assets_keys_path, 'r') as f:
    assets_keys = json.load(f)

########################################################
#         Add algo
########################################################

print('Adding algo...')
algo_key = client.add_algo({
    'name': ALGO['name'],
    'category': ALGO['category'],
    'file': ALGO['file'],
    'description': ALGO['description'],
    'permissions': ALGO['permissions'],
})

########################################################
#         Add traintuple
########################################################

print('Registering traintuple...')
traintuple_key = client.add_traintuple({
    'algo_key': algo_key,
    'data_manager_key': assets_keys['dataset_key'],
    'train_data_sample_keys': assets_keys['train_data_sample_keys']
})
assert traintuple_key, 'Missing traintuple key'

########################################################
#         Add testtuple
########################################################
print('Registering testtuple...')
testtuple_key = client.add_testtuple({
    'metric_keys': [assets_keys['metric_key']],
    'traintuple_key': traintuple_key,
    'data_manager_key': assets_keys['dataset_key'],
    'test_data_sample_keys': assets_keys['test_data_sample_keys'],
})
assert testtuple_key, 'Missing testtuple key'

########################################################
#         Save keys in json
########################################################

assets_keys['algo_constant'] = {
    'algo_key': algo_key,
    'traintuple_key': traintuple_key,
    'testtuple_key': testtuple_key,
}
with open(assets_keys_path, 'w') as f:
    json.dump(assets_keys, f, indent=2)

print(f'Assets keys have been saved to {os.path.abspath(assets_keys_path)}')
print('\nRun the following commands to track the status of the tuples:')
print(f'    substra get traintuple {traintuple_key} --profile node-1')
print(f'    substra get testtuple {testtuple_key} --profile node-1')
