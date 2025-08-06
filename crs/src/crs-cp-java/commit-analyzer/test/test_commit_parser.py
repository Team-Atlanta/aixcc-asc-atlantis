import pytest
from unittest.mock import patch, MagicMock
from src.commit_parser import CommitParser
from src.dataset import FunctionChange


@pytest.fixture
def mock_commits():
    return "commit1\ncommit2\ncommit3"


@pytest.fixture
def mock_diff():
    return """
    diff --git a/file.c b/file.c
index 83db48f..f735c60 100644
--- a/file.c
+++ b/file.c
@@ -1,3 +1,4 @@
int main() {
+    return 0;
}
    """


@pytest.fixture
def mock_old_file_content():
    return "int main() { return 0; }"


@pytest.fixture
def mock_new_file_content():
    return "int main() { int a; return 0; }"


@pytest.fixture
def commit_parser():
    return CommitParser("/fake/path", "main")


def test_get_commits(commit_parser, mock_commits):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_commits)
        commits = commit_parser.get_commits()

    assert commits == ["commit1", "commit2", "commit3"]


def test_get_diff(commit_parser, mock_diff):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_diff)
        diff = commit_parser.get_diff("commit1")

    assert mock_diff == diff


def test_get_changed_files(commit_parser, mock_diff):
    changed_files = commit_parser.get_changed_files(mock_diff)

    assert changed_files == {("a/", "file.c", "b/", "file.c")}


def test_get_file_content(commit_parser, mock_new_file_content):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_new_file_content)
        content = commit_parser.get_file_content("commit1", "file.c")

    assert "int main() { int a; return 0; }" in content


def test_get_parent_commit(commit_parser):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="parent_commit")
        parent_commit = commit_parser.get_parent_commit("commit1")

    assert parent_commit == "parent_commit"


def test_get_func_info(commit_parser, mock_new_file_content):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_new_file_content)
        with patch("src.commit_parser.CommitParser.parse_code") as mock_parse_code:
            mock_parse_code.return_value = {
                "main": MagicMock(code="int main() { int a; return 0; }")
            }
            func_info = commit_parser.get_func_info("commit1", "file.c", "c")

    assert "main" in func_info
    assert func_info["main"].code == "int main() { int a; return 0; }"


def test_parse_repo_function(
    commit_parser, mock_commits, mock_diff, mock_old_file_content, mock_new_file_content
):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout=mock_commits),  # get_commits
            MagicMock(stdout="commit subject"),  # get_subject (commit1)
            MagicMock(stdout="parent_commit"),  # get_parent_commit (commit1)
            MagicMock(stdout=mock_diff),  # get_diff (commit1)
            MagicMock(
                stdout=mock_new_file_content
            ),  # get_file_content (commit1, new file)
            MagicMock(
                stdout=mock_old_file_content
            ),  # get_file_content (parent_commit, old file)
            # Ignore commit, because this commit is dev commit.
            MagicMock(stdout="[IGNORE]"),  # get_subject (commit2)
            # Ignore commit, because this commit is initial commit.
            MagicMock(stdout="commit subject"),  # get_subject (commit3)
            MagicMock(stdout=""),  # get_parent_commit (commit3)
        ]
        with patch("commit_parser.CommitParser.parse_code") as mock_parse_code:
            mock_parse_code.side_effect = [
                {"main": MagicMock(code="int main() { return 0; }")},
                {"main": MagicMock(code="int main() { int a; return 0; }")},
            ]
            commit_info = next(commit_parser.parse_repo("function"))

    assert len(commit_info) == 1
    assert commit_info[0].commit_id == "commit1"
    # assert isinstance(commit_info[0], FunctionChange)
    assert commit_info[0].before_code == "int main() { return 0; }"
    assert commit_info[0].after_code == "int main() { int a; return 0; }"
