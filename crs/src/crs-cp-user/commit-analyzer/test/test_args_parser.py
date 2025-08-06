import pytest
import sys
from unittest.mock import patch
from src.args_parser import parse_arguments


def test_parse_arguments_default():
    test_args = [
        "prog",
        "-t",
        "/path/to/repo",
        "-w",
        "/path/to/workdir",
        "-o",
        "/path/to/output",
    ]
    with patch.object(sys, "argv", test_args):
        args = parse_arguments()
        assert args.target == "/path/to/repo"
        assert args.workdir == "/path/to/workdir"
        assert args.output == "/path/to/output"
        assert args.config == "CommitMultiClassConfig"
        assert not args.eval_config
        assert args.max_worker == 1


def test_parse_arguments_custom():
    test_args = [
        "prog",
        "-t",
        "/another/path/to/repo",
        "-w",
        "/another/path/to/workdir",
        "-o",
        "/another/path/to/output",
        "-c",
        "AnotherConfig",
        "--eval_config",
        "--max_worker",
        "2",
    ]
    with patch.object(sys, "argv", test_args):
        args = parse_arguments()
        assert args.target == "/another/path/to/repo"
        assert args.workdir == "/another/path/to/workdir"
        assert args.output == "/another/path/to/output"
        assert args.config == "AnotherConfig"
        assert args.eval_config
        assert args.max_worker == 2


def test_missing_required_argument_target():
    test_args = ["prog", "-w", "/path/to/workdir", "-o", "/path/to/output"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit):
            parse_arguments()


def test_missing_required_argument_workdir():
    test_args = ["prog", "-t", "/path/to/repo", "-o", "/path/to/output"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit):
            parse_arguments()


def test_missing_required_argument_output():
    test_args = ["prog", "-t", "/path/to/repo", "-w", "/path/to/workdir"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit):
            parse_arguments()


def test_invalid_max_worker():
    test_args = [
        "prog",
        "-t",
        "/path/to/repo",
        "-w",
        "/path/to/workdir",
        "-o",
        "/path/to/output",
        "--max_worker",
        "invalid",
    ]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit):
            parse_arguments()
