from pathlib import Path
from typing import Annotated

import pygit2
import yaml
from pydantic import AfterValidator, BaseModel

from loop.framework.detection.models import Detection

PathStr = Annotated[Path, AfterValidator(lambda x: Path(x))]


class ChallengeSource(BaseModel):
    key: str
    challenge_project_directory: Path
    source_directory: Path
    sanitizer_name: str
    harness_name: str

    @staticmethod
    def from_detection(detection: Detection, working_directory: Path):
        metadata = ChallengeProjectYaml.from_directory(working_directory)

        for source in metadata.cp_sources.values():
            repository = pygit2.Repository(
                path=str(working_directory / source.directory)
            )

            match repository.get(detection.bug_introduce_commit):
                case None:
                    continue
                case _:
                    return ChallengeSource(
                        key=source.key,
                        challenge_project_directory=working_directory,
                        source_directory=working_directory / source.directory,
                        sanitizer_name=metadata.sanitizers[detection.sanitizer_id],
                        harness_name=metadata.harnesses[detection.harness_id].name,
                    )

        raise ValueError(
            f"Could not find bug introduce commit {detection.bug_introduce_commit} in any source directory"
        )


class ChallengeProjectSource(BaseModel):
    key: str
    address: str
    directory: PathStr


class ChallengeProjectHarness(BaseModel):
    name: str
    source: PathStr
    binary: PathStr


class ChallengeProjectYaml(BaseModel):
    cp_sources: dict[str, ChallengeProjectSource]
    sanitizers: dict[str, str]
    harnesses: dict[str, ChallengeProjectHarness]

    @staticmethod
    def from_directory(directory: Path):
        yaml_path = directory / "project.yaml"

        return ChallengeProjectYaml.from_yaml(yaml_path)

    @staticmethod
    def from_yaml(yaml_path: Path):
        yaml_dict = yaml.safe_load(yaml_path.read_text())

        return ChallengeProjectYaml.model_validate(
            {
                **yaml_dict,
                "cp_sources": {
                    key: {
                        **value,
                        "key": key,
                        "directory": (
                            f"src/{key}"
                            if "directory" not in value
                            else value["directory"]
                        ),
                    }
                    for key, value in yaml_dict["cp_sources"].items()
                },
            }
        )
