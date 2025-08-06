import os
import json
import shutil
import tempfile
import subprocess

from log import debug, info, error

from fuzzercfg import FuzzerCfg
import constants


class GeneralFuzzer(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.process = None  # Keep the handle of the started process

    def fuzz_async(self):
        if self.is_fuzzing():
            self.stop()

        cmd = self.cfg.get_fuzz_command()
        debug(f"Start fuzzing with cmd: {cmd}")
        with open(self.cfg.fuzz_log, "w") as f:
            # store stdout/stderr output
            self.process = subprocess.Popen(cmd, shell=True, stdout=f, stderr=f)

    def is_fuzzing(self):
        if (self.process is not None) and (self.process.poll() is None):
            return True
        return False

    def stop(self):
        """
        NOTE: libfuzzer has a `stop_file` option, but it is not strong enough to stop the fuzzing process. Therefore, we kill the process directly.
        """
        if self.is_fuzzing():
            # Sends a SIGTERM signal
            self.process.terminate()
            # Wait for the process to terminate
            self.process.wait(5)
            # send SIGKILL
            if self.process.poll() is None:
                # None means process hasn't terminated
                self.process.kill()
            self.process = None

    def wait_and_stop(self, seconds):
        """
        Stop the fuzzing process after a specified time, None means wait forever.
        """
        if not self.is_fuzzing():
            return 0

        try:
            ret = self.process.wait(timeout=seconds)
            return ret
        except subprocess.TimeoutExpired:
            self.stop()
            return -1

    def fuzz_sync(self, seconds):
        """
        Start the fuzzing process and wait for a specified time, None means wait forever.
        """
        self.fuzz_async()
        return self.wait_and_stop(seconds)

    def get_artifact_dir(self):
        return self.cfg.artifact_dir

    def get_corpus_dir(self):
        return self.cfg.corpus_dir

    def add_corpus(self, added_corpus):
        # Get all files in the added_corpus directory
        for filename in os.listdir(added_corpus):
            source = os.path.join(added_corpus, filename)
            destination = os.path.join(self.get_corpus_dir(), filename)
            # Copy each file to the original corpus_dir
            # since Jazzer may delete some seeds, we catch the unhandled exception of file not found
            try:
                shutil.copy(source, destination)
            except FileNotFoundError as e:
                pass

    def get_fuzz_log(self):
        return self.cfg.fuzz_log

    def set_dict_file(self, dict_file):
        shutil.copy(dict_file, self.cfg.dict_file)


class SelfIntrospectionFuzzer(GeneralFuzzer):
    def __init__(self, gfuzzer):
        # cfg: not fuzz but dry run the seeds & do introspection
        cfg = FuzzerCfg.new_from_exist(
            gfuzzer.cfg,
            os.path.join(gfuzzer.cfg.work_dir, "self-introspection"),
            reset=True,
        )
        # - disable mutation
        cfg.set_option("-runs", "0")
        # - only use cov instrumentation
        cfg.set_option("--trace", "cov")
        # - enable introspection
        cfg.set_option("--self_introspection", cfg.introspection_file)

        super().__init__(cfg)

        self.add_corpus(gfuzzer.get_corpus_dir())
        # indeed the dict for introspection is optional
        self.set_dict_file(gfuzzer.cfg.dict_file)

    def introspect(self):
        if os.path.exists(self.cfg.introspection_file):
            os.remove(self.cfg.introspection_file)
        ret = self.fuzz_sync(constants.INTROSPECTION_TIMEOUT)
        if ret != 0:
            info(f"Self introspection return with non-zero ret code: {ret}, this does not necessarily mean code bug, perhaps meet timeout cases (cannot be resolved by keep_going)")
            info(f"Can check more detail in log file: {self.get_fuzz_log()}")

        if not os.path.exists(self.cfg.introspection_file):
            error(f"Introspection file {self.cfg.introspection_file} not found, introspection failed")
            return {}
        with open(self.cfg.introspection_file, "r") as f:
            return json.load(f)


class FocusedFuzzer(GeneralFuzzer):
    """
    Currently we only have specified dict, seeds, and instrumentation for focused fuzzing
    TODO:
    - selective mutation
    - grammar aware
    - semantic aware
    """

    def __init__(
        self,
        gfuzzer,
        focused_dicts,
        focused_seeds,
        focused_instru_includes,
        focused_fuzz_time,
    ):
        with tempfile.NamedTemporaryFile() as tmp_dict:
            tmp_dict.write("\n".join(focused_dicts).encode())
            tmp_dict.flush()

            # create a tmp work dir & copy all seeds into
            with tempfile.TemporaryDirectory() as to_dir:
                frm_corpus = gfuzzer.get_corpus_dir()
                for filename in os.listdir(frm_corpus):
                    if filename not in focused_seeds:
                        continue
                    source = os.path.join(frm_corpus, filename)
                    destination = os.path.join(to_dir, filename)
                    if os.path.isfile(source):
                        shutil.copy(source, destination)

                # focused fuzz cfg
                cfg = FuzzerCfg(
                    work_dir=os.path.join(gfuzzer.cfg.work_dir, "focused-fuzz"),
                    classpath=gfuzzer.cfg.classpath,
                    instrumentation_includes=focused_instru_includes,
                    harness=gfuzzer.cfg.harness,
                    total_fuzzing_time=focused_fuzz_time,
                    keep_going=gfuzzer.cfg.keep_going,
                    reset=True,
                )
                # set focused instrumentation
                # cfg.set_option("--instrumentation_includes", focused_instru_includes)

                super().__init__(cfg)

                # add focused dict
                self.set_dict_file(tmp_dict.name)
                # add focused corpus
                self.add_corpus(to_dir)
