import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(description="Commit Analyzer")
    parser.add_argument(
        "-t",
        "--target",
        type=str,
        help="The target repo path to be analyzed",
        required=True,
    )
    parser.add_argument(
        "-w",
        "--workdir",
        type=str,
        help="The directory to save intermediate outputs",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="The directory to output the results",
        required=True,
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Please enter the configuration to set up the prompt.",
        default="CommitMultiClassConfig",
    )
    parser.add_argument(
        "--eval_config",
        action="store_true",
        help="Evaluate the configuration with predefined test cases",
    )
    parser.add_argument(
        "--max_worker",
        type=int,
        help="Number of work counts to thread in parallel",
        default=1,
    )
    return parser.parse_args()
