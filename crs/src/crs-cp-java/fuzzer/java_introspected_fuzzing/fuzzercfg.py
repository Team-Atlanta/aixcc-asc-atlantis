import os
import shutil

import constants


class FuzzerCfg:
    def __init__(
        self,
        work_dir,
        classpath,
        instrumentation_includes,
        harness,
        total_fuzzing_time,
        keep_going,
        corpus_dir=None,
        dict_file=None,
        log_file=None,
        reset=False,
    ):
        # fuzzer engine
        self.jazzer = constants.JAZZER
        # compiled fuzz_driver path
        self.harness = harness
        # classpath
        self.classpath = classpath
        # instrumentation includes
        self.instrumentation_includes = instrumentation_includes
        # max total time
        self.total_fuzzing_time = total_fuzzing_time
        # keep going
        self.keep_going = keep_going

        # prepare work dir & contents
        self.work_dir = work_dir
        if reset and os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
        os.makedirs(self.work_dir, exist_ok=True)

        # log
        if log_file:
            self.fuzz_log = log_file
        else:
            self.fuzz_log = os.path.join(work_dir, "fuzz.log")
            if reset:
                with open(self.fuzz_log, "w") as f:
                    f.write("")

        # dict
        if dict_file:
            self.dict_file = dict_file
        else:
            self.dict_file = os.path.join(work_dir, "fuzz.dict")
            if reset or (not os.path.exists(self.dict_file)):
                # add a placeholder dict file if not exists
                with open(self.dict_file, "w") as f:
                    f.write("#")

        # corpus
        if corpus_dir:
            self.corpus_dir = corpus_dir
        else:
            self.corpus_dir = os.path.join(work_dir, "corpus_dir")
            if reset:
                if os.path.exists(self.corpus_dir):
                    shutil.rmtree(self.corpus_dir)
            os.makedirs(self.corpus_dir, exist_ok=True)

        # artifact
        self.artifact_dir = os.path.join(work_dir, "artifacts")
        # has already been reset when reset work_dir if reset is True
        os.makedirs(self.artifact_dir, exist_ok=True)

        # reproducer
        self.reproducer_dir = os.path.join(work_dir, "reproducer")
        # has already been reset when reset work_dir if reset is True
        os.makedirs(self.reproducer_dir, exist_ok=True)

        # scores_dir
        self.scores_dir = os.path.join(work_dir, "scores_dir")
        # has already been reset when reset work_dir if reset is True
        os.makedirs(self.scores_dir, exist_ok=True)

        # dump instrumented class files (introspection only)
        self.dump_classes_dir = os.path.join(work_dir, "dump-classes")
        # has already been reset when reset work_dir if reset is True
        os.makedirs(self.dump_classes_dir, exist_ok=True)

        # introspection file (introspection only)
        self.introspection_file = os.path.join(work_dir, "introspection.json")

        # TODO: support directed fuzzer enabled options
        self.options = {
            # jazzer options
            "--agent_path": self.jazzer + "_standalone_deploy.jar",
            "--jvm_args": "\"-Djdk.attach.allowAttachSelf=true:-XX\:+StartAttachListener:-Xmx4g:-XX\:ParallelGCThreads=2:-XX\:ConcGCThreads=1:-Djava.util.concurrent.ForkJoinPool.common.parallelism=2\"",
            #"--instrumentation_excludes": "org.apache.logging.**:com.fasterxml.**:org.apache.commons.**",
            "--disabled_hooks": "com.code_intelligence.jazzer.sanitizers.IntegerOverflow",
            "--experimental_mutator": "1",
            "--reproducer_path": self.reproducer_dir,
            "--dump_classes_dir": self.dump_classes_dir,
            #"--instrumentation_includes": self.instrumentation_includes,
            "--cp": self.classpath,
            "--target_class": self.harness,
            "--keep_going": self.keep_going,
            # libfuzzer options
            "-use_value_profile": "1",
            "-reload": "1",
            "-close_fd_mask": "1",
            "-timeout": f"{constants.EXECUTION_TIMEOUT}",
            "-max_total_time": f"{self.total_fuzzing_time}",
            "-artifact_prefix": f"{self.artifact_dir}",
            "-dict": self.dict_file,
            "-target_distance_dir": self.scores_dir,
        }

    @staticmethod
    def new_from_exist(cfg, work_dir, reset):
        return FuzzerCfg(
            work_dir=work_dir,
            classpath=cfg.classpath,
            instrumentation_includes=cfg.instrumentation_includes,
            harness=cfg.harness,
            total_fuzzing_time=cfg.total_fuzzing_time,
            keep_going=cfg.keep_going,
            reset=reset,
        )

    def set_option(self, key, value):
        self.options[key] = value

    def unset_option(self, key):
        del self.options[key]

    def get_fuzz_command(self):
        # fuzz options
        return (
            self.jazzer
            + " "
            + " ".join([f"{k}={v}" for k, v in self.options.items()])
            + " "
            + self.corpus_dir
        )
