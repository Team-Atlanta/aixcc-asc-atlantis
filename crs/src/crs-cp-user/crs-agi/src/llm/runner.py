import time
import sys
import litellm
import openai

from abc import abstractmethod

from loguru import logger

from .prompt import load_prompt
from .errors import (PluginErrorGivingUp, PluginErrorRetry,
    PluginErrorTimeout, PluginSuccess, PluginErrorTokenLimit)


# running strategies
RECOVERY_BACKTRACE = (1<<0)     # remove one prompt entries at a time
RECOVERY_RETRY     = (1<<1)     # reset the prompt (add a summary / hint)
RECOVERY_GIVINGUP  = (1<<2)     # llm gave up, but give another try
RECOVERY_MAXOUT    = (1<<3)     # token maxout
RECOVERY_ALL       = \
    RECOVERY_BACKTRACE \
    | RECOVERY_RETRY \
    | RECOVERY_GIVINGUP \
    | RECOVERY_MAXOUT

STATE_INITIATING   = 1
STATE_TIMEOUT      = 2
STATE_RUNNING      = 3
STATE_SUCCESS      = 4
STATE_ERROR        = 5
STATE_TERMINATED   = 6
STATE_GIVINGUP     = 7
STATE_RETRYING     = 8
STATE_TOKEN_MAXOUT = 9

class Oracle:
    name: str

    # any none None value considered an oracle is triggered
    @abstractmethod
    def check(self, runner):
        pass

# CRSPlanner
# CRSFuzzer
# CRSAnalyzer

class LLMRunner:
    def __init__(self, opts, llm, prompt, workspace,
                 channels=None, oracles=None, recovery=RECOVERY_ALL, timeout=sys.maxsize):
        self.prompt0 = prompt.copy()
        self.opts = opts
        self.llm = llm
        self.workspace = workspace
        self.channels = channels
        self.oracles = oracles or []
        self.recovery = recovery
        self.timeout = timeout
        self.started = 0
        self.elapased = 0
        self.state = STATE_INITIATING
        self.openai_errors = 0

    def run(self):
        self.generations = 0
        self.started = time.time()
        self.prompt = self.prompt0.copy()

        self.exit_reason = None
        while self.openai_errors < 6:
            # TODO
            # check any messages from the shared channel

            # run one generation
            self.run1()
            self.save_chat()

            logger.info(f"[{self.generations}] Exit: {self.state}, Reason: {self.exit_reason}")

            # terminate the execution
            self.oracle_results = self.check_oracles()
            if self.state == STATE_TIMEOUT \
               or self.state == STATE_SUCCESS:
                return (self.state, self.oracle_results)

            # generation-wide recovery
            if self.state == STATE_GIVINGUP:
                self.prompt = self.prompt0.copy()
                self.prompt.append(
                    load_prompt("retry_after_givingup.txt",
                                tries=self.generations,
                                reason=self.exit_reason))
                continue

            if self.state == STATE_RETRYING:
                self.prompt = self.prompt0.copy()
                self.prompt.append(
                    load_prompt("retry.txt",
                                tries=self.generations,
                                reason=self.exit_reason[0],
                                summary=self.exit_reason[1]))
                continue

            if self.state == STATE_MAXTOKENS:
                pass

        return (STATE_TERMINATED, None)

    def run1(self):
        self.state = STATE_RUNNING
        self.generations += 1
        self.elapased = time.time() - self.started

        sessions = 0
        backoff = 1
        prompt1 = self.prompt.copy()

        while True:
            sessions += 1
            self.elapsed = time.time() - self.started

            if self.elapsed > self.timeout:
                self.state = STATE_TIMEOUT
                logger.info("[%d.%d] Session timeout @%.3f" \
                            % (self.generations, sessions, self.elapsed))
                break

            logger.info("[%d.%d] Session started (%.3f sec)" \
                        % (self.generations, sessions, self.elapsed))
            try:
                self.state = STATE_RUNNING
                self.llm.run(self.prompt)

                # adjust backoff on success, but min to 1
                backoff = max(backoff//2, 1)

            except (openai.RateLimitError,
                    openai.APITimeoutError,
                    openai.BadRequestError,
                    openai.ConflictError,
                    openai.InternalServerError,
                    openai.UnprocessableEntityError) as e:
                # naively give up after some time, we shouldn't waste too much time if something isn't set up right
                self.openai_errors += 1
                time.sleep(min(2 ** self.openai_errors, 8))
                self.state = STATE_GIVINGUP
                self.exit_reason = \
                    f"Encountered an unexpected error during the execution:\n{e}"
                return
            except (openai.APIConnectionError,
                    openai.NotFoundError,
                    openai.AuthenticationError,
                    openai.PermissionDeniedError) as e:
                self.openai_errors = 1000 # immediately give up
                self.state = STATE_GIVINGUP
                self.exit_reason = \
                    f"Encountered an unexpected error during the execution:\n{e}"
                return
            except PluginSuccess as e:
                self.state = STATE_SUCCESS
                self.exit_reason = e.summary
                return
            except PluginErrorGivingUp as e:
                self.state = STATE_GIVINGUP
                self.exit_reason = e.reason
                return
            except PluginErrorRetry as e:
                self.state = STATE_RETRYING
                self.exit_reason = (e.reason, e.summary)
                return
            except Exception as e:
                # NOTE. https://litellm.vercel.app/docs/exception_mapping
                if self.recovery & RECOVERY_MAXOUT \
                   and isinstance(e, litellm.ContextWindowExceededError):
                    # TODO
                    #  summarize the past session
                    #  and restart the generation
                    pass

                if self.recovery & RECOVERY_BACKTRACE:
                    self.prompt.pop(backoff)
                    backoff *= 2

                    # if all the history cleaned up, new generation
                    if self.prompt.len() <= prompt1.len():
                        self.state = STATE_GIVINGUP
                        self.exit_reason = \
                            f"Encountered an unexpected error during the execution:\n{e}"
                        return

                    logger.info("Backtracing the prompt (#prompts=%d, #backoff=%d)"
                                % (self.prompt.len(), backoff))

                    # otherwise, backoff
                    continue

                self.state = STATE_TERMINATED
                self.exit_reason = f"{e}"
                return

    def check_oracles(self):
        out = {}
        for o in self.oracles:
            rtn = o.check(self)
            if rtn is not None:
                out[o.name] = rtn
        return out

    def save_chat(self):
        if self.opts.delete:
            return

        pn = f"chat-{self.generations}.json"
        self.prompt.store_to(self.workspace.history / pn)


