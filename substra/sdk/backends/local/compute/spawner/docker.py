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
import logging
import pathlib
import string
import tempfile
import docker
from substra.sdk.backends.local.compute.spawner.base import BaseSpawner, ExecutionError
from substra.sdk.archive import uncompress

logger = logging.getLogger(__name__)

ROOT_DIR = "/substra_internal"

DOCKER_VOLUMES = {
    "_VOLUME_INPUT_DATASAMPLES": {"bind": f"{ROOT_DIR}/data_samples", "mode": "ro"},
    "_VOLUME_INPUT_MODELS": {"bind": f"{ROOT_DIR}/in_models", "mode": "ro"},
    "_VOLUME_OUTPUT_MODELS": {"bind": f"{ROOT_DIR}/out_models", "mode": "rw"},
    "_VOLUME_OPENER": {"bind": f"{ROOT_DIR}/opener/__init__.py", "mode": "ro"},
    "_VOLUME_OUTPUT_PRED": {"bind": f"{ROOT_DIR}/pred", "mode": "rw"},
    "_VOLUME_OUTPUT_PERF": {"bind": f"{ROOT_DIR}/perf", "mode": "rw"},
    "_VOLUME_LOCAL": {"bind": f"{ROOT_DIR}/local", "mode": "rw"},
    "_VOLUME_CHAINKEYS": {"bind": f"{ROOT_DIR}/chainkeys", "mode": "rw"},
}


class Docker(BaseSpawner):
    """Wrapper around docker daemon to execute a command in a container."""

    def __init__(self, local_worker_dir: pathlib.Path):
        try:
            self._docker = docker.from_env()
        except docker.errors.DockerException as e:
            raise ConnectionError(
                "Couldn't get the Docker client from environment variables. "
                "Is your Docker server running ?\n"
                "Docker error : {0}".format(e)
            )
        super().__init__(local_worker_dir=local_worker_dir)

    def spawn(
        self,
        name,
        archive_path,
        command_template: string.Template,
        local_volumes=None,
        envs=None,
    ):
        """Spawn a docker container (blocking)."""
        with tempfile.TemporaryDirectory(dir=self._local_worker_dir) as tmpdir:
            image_exists = False
            try:
                self._docker.images.get(name=name)
                image_exists = True
            except docker.errors.ImageNotFound:
                pass

            if not image_exists:
                try:
                    logger.debug('Did not find the Docker image %s - building it', name)
                    uncompress(archive_path, tmpdir)
                    self._docker.images.build(path=tmpdir, tag=name, rm=True)
                except docker.errors.BuildError as exc:
                    for line in exc.build_log:
                        if 'stream' in line:
                            logger.error(line['stream'].strip())
                    raise

        # format the command to replace each occurrence of a DOCKER_VOLUMES's key
        # by its "bind" value
        volumes_format = {
            volume_name: volume_path["bind"]
            for volume_name, volume_path in DOCKER_VOLUMES.items()
        }
        command = command_template.substitute(**volumes_format)

        # create the volumes dict for docker by binding the local_volumes and the DOCKER_VOLUME
        volumes_docker = {
            volume_path: DOCKER_VOLUMES[volume_name]
            for volume_name, volume_path in local_volumes.items()
        }

        container = self._docker.containers.run(
            name,
            command=command,
            volumes=volumes_docker or {},
            environment=envs,
            remove=False,
            detach=True,
            tty=True,
            stdin_open=True,
            shm_size='8G',
        )

        execution_logs = []
        for line in container.logs(stream=True, stdout=True, stderr=True):
            execution_logs.append(line.decode('utf-8'))

        r = container.wait()
        execution_logs_str = ''.join(execution_logs)
        exit_code = r['StatusCode']
        if exit_code != 0:
            logger.error("\n\nExecution logs: %s", execution_logs_str)
            raise ExecutionError(f"Container '{name}' exited with status code '{exit_code}'")

        container.remove()
        return execution_logs_str
