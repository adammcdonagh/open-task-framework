# monkey patch lovely pytest docker plugin
# lovely-pytest-docker is no longer maintained, so we need to monkey patch it
# to use docker compose instead as docker-compose v1 is no longer part of the
# GitHub Actions runner
from lovely.pytest.docker.compose import DockerComposeExecutor, execute


def docker_compose_executor(self, *subcommand):
    command = ["docker", "compose", "--project-directory", self.project_directory]
    for compose_file in self._compose_files:  # pylint: disable=protected-access
        command.append("-f")
        command.append(compose_file)
    command.append("-p")
    command.append(self._project_name)  # pylint: disable=protected-access
    command += subcommand
    return execute(command)


DockerComposeExecutor.execute = docker_compose_executor
