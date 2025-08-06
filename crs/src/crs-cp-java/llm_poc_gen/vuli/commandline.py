import argparse
import os


def get_command_line_parser():
    parser = argparse.ArgumentParser(description="vul.i")
    parser.add_argument(
        "--cp_dir",
        required=True,
        type=str,
        help="The path to the cp directory (required)",
    )
    parser.add_argument(
        "--harnesses",
        type=str,
        help="This option allows you to specify the IDs of the harnesses you want to test. If you want to test multiple harnesses, you can list their IDs separated by commas. If this option is not provided, the test will be performed on all available harnesses.",
    )
    parser.add_argument(
        "--joern_dir",
        type=str,
        help="The path to the Joern directory",
    )
    parser.add_argument(
        "--output_dir",
        default=os.path.abspath("output"),
        type=str,
        help="The path to the output directory",
    )
    parser.add_argument("--python_path", type=str, help="The path to python")
    parser.add_argument(
        "--no-reuse",
        action="store_true",
        dest="no_reuse",
        help="Reuse prepared result in output/blackboard",
    )
    parser.add_argument(
        "--n_response", default=10, type=int, help="The number of responses for llm"
    )
    parser.add_argument(
        "--temperature",
        default=1.0,
        type=float,
        help="Temperature(=Randomness) for llm",
    )
    parser.add_argument(
        "--budget", default=80.0, type=float, help="Maximum Budget For LLM (in USD)"
    )
    parser.add_argument(
        "--limit",
        default=300,
        type=int,
        help="Maximum Time Limit For Continuous Failure (in minute)",
    )
    return parser.parse_args()
