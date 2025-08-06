from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from commit_parser import CommitParser
from projparser import ProjectParser
from completion import OpenAICompletion
from collections import defaultdict
from model import GPT4o
import os
from typing import Dict

# from logger import setup_logger
from config import ConfigFactory
from prompt import PromptBuilder
import json
from chat import OpenAIChat
from LLMManager import LLMManager
import util as util
import colorlog
import logging
from args_parser import parse_arguments

logger = logging.getLogger("Run")


def setup_logging():
    log_colors = {
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    }

    log_format = "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure the logging system
    handler = logging.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(log_format, log_colors=log_colors))

    logging.basicConfig(level=logging.ERROR, handlers=[handler])


def job_submit(executor, target, config, chat, LLMManager):
    prompt = (
        PromptBuilder()
        .add_query(target, config)
        .add_system_prompt(config.get_system_prompt(chat.bug_type))
        .build()
    )
    if len(prompt.query.strip()) == 0:
        return None
    completion = OpenAICompletion(
        system_prompt=prompt.system_prompt,
        user_prompt=[{"question": prompt.query, "answer": ""}],
        model=GPT4o(),
        functions=config.functions,
        function_call=config.function_call,
    )
    changed_functions = [
        func_info.function_name for func_info in target.function_changes
    ]

    return executor.submit(
        chat.complete, target.commit_id, changed_functions, completion, LLMManager
    )


def analyze_src(
    src_name,
    ref,
    target_path,
    output_file,
    config,
    max_worker,
    sanitizers,
    llm_manager,
) -> Dict:
    result = defaultdict(set)
    chat_objects = []

    # TODO Reduce the time overhead by parsing the commit and sanitizer information in advance
    target_commits = CommitParser(target_path, ref).parse_repo(config.analyze_unit)

    if config.classification == "binary":
        for bug_type in sanitizers.values():
            print(f"Target bugs: {bug_type}")
            chat_objects.append(OpenAIChat([bug_type]))
    elif config.classification == "multi-class":
        chat_objects.append(OpenAIChat(list(sanitizers.values())))

    count_invalid = 0
    total_cost = 0
    cost_exceeded = False
    for targets in target_commits:
        print(f"Required queries: {len(targets) * len(chat_objects)}")
        futures = []

        with ThreadPoolExecutor(max_workers=max_worker) as executor:
            for target in targets:
                for chat in chat_objects:
                    future = job_submit(executor, target, config, chat, llm_manager)

                    if future is not None:
                        futures.append(future)

            file_lock = threading.Lock()
            san2id = {v: k for k, v in sanitizers.items()}
            if len(sanitizers) != len(san2id):
                print(
                    "Error: Duplicate sanitizer id found. The candidated bugs may be incorrect."
                )

            for future in as_completed(futures):
                commit, completion_result, cost, bug_type, candidate_func = (
                    future.result()
                )
                print(
                    f"{commit}, {completion_result}, {cost}, {bug_type}, {candidate_func}"
                )
                total_cost += cost
                if completion_result == "benign":
                    pass
                elif completion_result == "invalid":
                    count_invalid += 1
                    pass
                elif completion_result == "exceed":
                    cost_exceeded = True
                    pass
                else:
                    with file_lock:
                        san_id = san2id[bug_type]
                        if san_id not in result[commit]:
                            result[commit].add(f"{san_id}")
                            with open(output_file, "a") as f:
                                f.write(
                                    f"{src_name}, {commit}, {san_id}, {candidate_func}\n"
                                )

        if cost_exceeded or llm_manager.cost > config.budget:
            break

    print("Total cost: ", total_cost)
    print("Invalid response count: ", count_invalid)
    return result


def analyze_repo(target_dir, output_file, config, max_worker):
    project_parser = ProjectParser(target_dir)
    repo_info = project_parser.get_repo_info()
    sanitizers = project_parser.get_sanitizer()

    # Initialize output file
    dirname = os.path.dirname(output_file)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)

    with open(output_file, "w") as _:
        pass

    llm_manager = LLMManager(config.budget)
    results = defaultdict(set)
    for subdir, ref in repo_info:
        target_path = os.path.join(target_dir, "src", subdir)
        result = analyze_src(
            subdir,
            ref,
            target_path,
            output_file,
            config,
            max_worker,
            sanitizers,
            llm_manager,
        )

        for key, value in result.items():
            results[key].update(value)

        if llm_manager.cost > config.budget:
            break
    return results


def eval_on_testset(target_projects, output_file, config, max_worker):
    from parse_repo import parse_repo
    from evaluation import BasicEvaluator  # , StrictEvaluator
    from tempfile import NamedTemporaryFile

    gt_path = "../asc-iAPI/cpv_db.json"
    with open(gt_path, "r") as f:
        gt = json.load(f)

    results = {}
    for proj_name, proj_info in target_projects.items():
        proj_path = proj_info["proj_path"]
        proj_changes = {}
        for source, changes in parse_repo(proj_path).items():
            proj_changes.update(changes)

        if proj_name not in gt:
            print(f"Groundtruth for {proj_name} not found.")
            continue

        groundtruth = {}
        for _, cpv_value in gt[proj_name].items():
            groundtruth[cpv_value["commit"]] = cpv_value["sanitizer"]

        # with NamedTemporaryFile("w", delete=True) as f:
        with open(f"outputs/test-eval-{proj_name}.txt", "w") as f:
            temp_output = f.name
            analyze_results = analyze_repo(proj_path, temp_output, config, max_worker)
        metrics = BasicEvaluator().eval_accuracy(
            analyze_results, groundtruth, proj_changes, output_file
        )
        results[proj_name] = metrics

        with open(output_file, "w") as f:
            json.dump(results, f, indent=4)


def main():
    args = parse_arguments()
    target_dir = args.target
    # working_dir = args.workdir
    output_file = args.output
    eval_config = args.eval_config
    max_worker = args.max_worker
    config = ConfigFactory.createConfig(args.config)

    if eval_config:
        target_projects = {
            "linux kernel": {"proj_path": "../cp-linux-exemplar"},
            # "Mock CP": {"proj_path": "../mock-cp"},
            # "nginx": {"proj_path": "../challenge-004-nginx-cp"},
            # "zstd": {"proj_path": "../cp-zstd-exemplar"},
            # "hoextdown": {"proj_path": "../cp-hoextdown-exemplar"},
        }
        eval_on_testset(
            target_projects=target_projects,
            output_file=output_file,
            config=config,
            max_worker=max_worker,
        )
    else:
        analyze_repo(
            target_dir=target_dir,
            output_file=output_file,
            config=config,
            max_worker=max_worker,
        )


if __name__ == "__main__":
    setup_logging()
    main()
