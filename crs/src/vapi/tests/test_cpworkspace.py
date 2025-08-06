# pylint: disable=unused-argument
from uuid import uuid4

from competition_api.audit import Auditor
from competition_api.cp_workspace import CPWorkspace


class TestCPWorkspace:
    @staticmethod
    async def test_init(test_project_yaml, repo):
        async with CPWorkspace(
            test_project_yaml["cp_name"], Auditor(uuid4())
        ) as workspace:
            assert workspace.workdir
            assert workspace.project_yaml == test_project_yaml
            assert workspace.repo
