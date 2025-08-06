import pytest
import logging
from unittest.mock import mock_open, patch
from src.projparser import ProjectParser


@pytest.fixture
def caplog_fixture(caplog):
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def valid_yaml_content():
    return """
    cp_sources:
        linux_kernel:
            address: git@github.com:Team-Atlanta/cp-linux-exemplar-source.git
            ref: test

    sanitizers:
       id_1: "KASAN: slab-out-of-bounds"
       id_2: "KASAN: stack-out-of-bounds"
       id_3: "KASAN: use-after-free"
    """


@pytest.fixture
def malformed_yaml_content():
    return """
    sanitizers: [address, undefined
    """


@pytest.fixture
def target_path():
    return "/test/path"


def create_project_parser(target_path, read_data):
    with patch("builtins.open", mock_open(read_data=read_data)):
        return ProjectParser(target_path)


def test_get_sanitizer_valid(target_path, valid_yaml_content):
    project_parser = create_project_parser(target_path, valid_yaml_content)
    result = project_parser.get_sanitizer()
    assert result == {
        "id_1": "KASAN: slab-out-of-bounds",
        "id_2": "KASAN: stack-out-of-bounds",
        "id_3": "KASAN: use-after-free",
    }


def test_get_sanitizer_malformed(target_path, malformed_yaml_content, caplog_fixture):
    project_parser = create_project_parser(target_path, malformed_yaml_content)
    result = project_parser.get_sanitizer()
    assert result == {}
    assert "Exception in project yaml parsing" in caplog_fixture.text


def test_get_repo_info(target_path, valid_yaml_content):
    project_parser = create_project_parser(target_path, valid_yaml_content)
    subdir, ref = project_parser.get_repo_info()[0]
    assert subdir == "linux_kernel"
    assert ref == "test"


def test_get_sanitizer_file_not_found(target_path, caplog_fixture):
    project_parser = ProjectParser(target_path)
    result = project_parser.get_sanitizer()
    assert result == {}
    assert "File not found error" in caplog_fixture.text
