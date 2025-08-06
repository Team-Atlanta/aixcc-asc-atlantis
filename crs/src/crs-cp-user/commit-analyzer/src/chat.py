from typing import List, Tuple
import logging


class OpenAIChat:
    def __init__(self, _bug_types: List):
        self.possible_answers = _bug_types + ["vulnerable", "benign"]
        self.bug_type = _bug_types
        self.logger = logging.getLogger("OpenAIChat")

        if len(_bug_types) < 1:
            self.logger.error("answer_list should be larger than 1")

    def pinpoint_function(
        self, completion, candidate_functions, answer, llm_manager
    ) -> Tuple[str, float]:
        if len(candidate_functions) == 1:
            return candidate_functions[0], 0

        completion.response_format = {"type": "json_object"}
        completion.continue_chat(
            response=answer,
            question=f"""Please pinpoint the function that has the vulnerability.
            Choose answer from the list: {list(set(candidate_functions))}.
            Output should be formatted as JSON object like: {{'answer': ...}}.""",
        )

        response, cost = completion.create(llm_manager)
        completion_result = completion.parse_response(
            response=response, possible_answers=candidate_functions
        )
        if (
            completion_result == "error"
            or completion_result == "exceed"
            or completion_result == "invalid"
        ):
            completion_result = ""

        return completion_result, cost

    def complete(
        self, commit_id, candidate_functions, completion, llm_manager
    ) -> Tuple[str, str, float, str, str]:
        tcost = 0
        trial_count = 0
        while trial_count < 2:
            (response, cost) = completion.create(llm_manager)
            trial_count += 1
            tcost += cost

            completion_result = completion.parse_response(
                response=response, possible_answers=self.possible_answers
            )

            if completion_result == "vulnerable":
                if len(self.bug_type) == 1:
                    func, cost = self.pinpoint_function(
                        completion, candidate_functions, response[0], llm_manager
                    )
                    tcost += cost
                    return commit_id, "vulnerable", tcost, self.bug_type[0], func
                elif len(self.bug_type) == 0:
                    return commit_id, "invalid", tcost, "None", ""
                else:
                    self.logger.error(
                        "Prompt need to be refined because it cannot choose one among multiple types."
                    )
                    completion.response_format = {"type": "json_object"}
                    completion.continue_chat(
                        response=response[0],
                        question=f"""Is it vulnerble or not? 
                        Choose answer from the list: {list(set(self.possible_answers) - set(['vulnerable']))}.
                        Output should be formatted as JSON object like: {{'answer': ...}}.""",
                    )
            elif completion_result == "invalid":
                # TODO Need update to consider mutli-class classification
                completion.response_format = {"type": "json_object"}
                completion.continue_chat(
                    response=response[0],
                    question=f"""Is it vulnerble or not? 
                    Choose answer from the list: {list(set(self.possible_answers) - set(['vulnerable']))}.
                    Output should be formatted as JSON object like: {{'answer': ...}}.""",
                )
                print("Invalid response. Continue chat.")
            elif completion_result == "exceed":
                return commit_id, "exceed", tcost, "exceed", ""
            elif completion_result == "error":
                break
            elif completion_result == "benign":
                return commit_id, completion_result, tcost, completion_result, ""
            else:
                func, cost = self.pinpoint_function(
                    completion, candidate_functions, response[0], llm_manager
                )
                tcost += cost
                return commit_id, completion_result, tcost, completion_result, func

        return commit_id, "invalid", tcost, "invalid", ""
