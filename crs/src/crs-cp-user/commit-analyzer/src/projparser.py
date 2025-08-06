import os
import yaml
import logging

from typing import Dict, List, Tuple


class ProjectParser:
    def __init__(self, target_path) -> None:
        self.logger = logging.getLogger("ProjectParser")
        self.target_path = target_path
        self.data = self.load_project_yaml()

    def load_project_yaml(self) -> Dict:
        try:
            with open(os.path.join(self.target_path, "project.yaml"), "r") as stream:
                try:
                    data = yaml.safe_load(stream)
                    return data

                except Exception as e:
                    self.logger.error("Exception in project yaml parsing: %s", e)
                    return dict()
        except FileNotFoundError as e:
            self.logger.error("File not found error: %s", e)
            return dict()

    def get_sanitizer(self) -> Dict:
        sanitizers = self.data.get("sanitizers", {})
        return sanitizers

    def get_repo_info(self) -> List[Tuple[str, str]]:
        src_subdir = self.data.get("cp_sources", {})

        repo_info = []
        for subdir in src_subdir.keys():
            try:
                repo_info.append((subdir, src_subdir[subdir].get("ref", "main")))
            except AttributeError:
                self.logger.info("No branch info found. Using main branch.")
                repo_info.append((subdir, "main"))

        return repo_info
