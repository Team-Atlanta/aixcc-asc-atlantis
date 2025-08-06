import time
import random
import traceback

from fuzzer import GeneralFuzzer, FocusedFuzzer
from introspector import Introspector
import util

from log import debug, error, info, warn


class IntrospectedFuzzing(object):

    def __init__(self, general_cfg):
        self.general_cfg = general_cfg

    def run(self):
        """
        Main logic of introspected fuzzing.
        """

        util.wait_until_service_alive()

        # run general fuzzing
        # gfuzzer = GeneralFuzzer(self.general_cfg)
        # gfuzzer.fuzz_async()
        # NOTE: We attach to existing general fuzzing instead of controling it
        # - 1. we read general fuzzing's log
        # - 2. we add corpus to general fuzzing
        gfuzzer = GeneralFuzzer(self.general_cfg)

        introspector = Introspector()

        # monitor general fuzzing process
        while True:
            time.sleep(60)

            try:
                if introspector.is_fuzzing_stuck(gfuzzer):
                    info("General fuzzing is stuck. Do introspection.")

                    focused_fuzz_cfgs = introspector.introspect(gfuzzer)
                    if not focused_fuzz_cfgs or len(focused_fuzz_cfgs) == 0:
                        info("No focused fuzz cfg generated.")
                        # in this case, usually system is busy now (timeout etc), we sleep a bit more
                        time.sleep(120)
                        continue
                    info(f"There are {len(focused_fuzz_cfgs)} focused fuzz cfgs.")

                    # TODO: use all instead of the 1st one
                    # randomly pick one focused fuzzer currently
                    ff_cfg = random.choice(focused_fuzz_cfgs)
                    info(f"Select a focused fuzz cfg: {ff_cfg}")
                    ffuzzer = FocusedFuzzer(
                        gfuzzer = ff_cfg[0],
                        focused_dicts = ff_cfg[1],
                        focused_seeds = ff_cfg[2],
                        focused_instru_includes = ff_cfg[3],
                        focused_fuzz_time = ff_cfg[4]
                        )

                    info("Run focused fuzzing.")
                    ffuzzer.fuzz_async()

                    while True:
                        if not ffuzzer.is_fuzzing():
                            info(
                                f"Focused fuzzing result: {introspector.is_focused_goal_reached(ffuzzer)}"
                            )
                            # add back the corpus no matter it reached the goal or not
                            info(
                                f"Add corpus from {ffuzzer.get_corpus_dir()} to {gfuzzer.get_corpus_dir()}"
                            )
                            gfuzzer.add_corpus(ffuzzer.get_corpus_dir())
                            # after adding corpus, we wait a while to let general fuzzing absorb the added corpus
                            time.sleep(420)
                            break

                        else:
                            # sleep a while for next check
                            time.sleep(30)

                else:
                    # sleep a while for next check
                    debug("General fuzzing is not stuck, sleep & watch.")

            except Exception as e:
                error(f"Introspection Loop Error: {e}")
                error(traceback.format_exc())
