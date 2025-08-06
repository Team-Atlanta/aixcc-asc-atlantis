import os
import re
import json
import shutil
import tempfile
import constants
import traceback

from log import debug, error, info, warn

from fuzzer import SelfIntrospectionFuzzer, FocusedFuzzer
import util


class LibfuzzerLogParser:
    # TODO: this need to adapt to CRS log pattern
    LIBFUZZER_COV_LINE_PTRN = re.compile(r"^#(\d+).*cov: (\d+) ft: (\d+)")

    @staticmethod
    def parse_log(log_file):
        """
        Parse libfuzzer log file to get coverage info.
        """
        with open(log_file, "rb") as f:
            lines = None
            try:
                fuzzlog = f.read(-1)
                # Some crashes can mess up the libfuzzer output and raise decode error.
                fuzzlog = fuzzlog.decode("utf-8", errors="ignore")
                lines = fuzzlog.split("\n")
            except Exception as e:
                error("Error parsing libfuzzer log file %s: %s" % (log_file, e))
                error(traceback.format_exc())

            if not lines:
                return None

            return LibfuzzerLogParser._parse_fuzz_status_lines_from_libfuzzer_logs(
                lines
            )

    @staticmethod
    def _parse_fuzz_status_lines_from_libfuzzer_logs(lines):
        """
        Parses <round no, cov and ft> from libFuzzer logs.
        """

        fuzz_statuses = []

        for line in lines:
            if line.startswith("#"):
                # Parses cov line to get the round number.
                match = LibfuzzerLogParser.LIBFUZZER_COV_LINE_PTRN.match(line)
                if not match:
                    continue
                roundno, cov, ft = (
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3)),
                )
                fuzz_statuses.append((roundno, cov, ft))

        # we do not need full log, last X status lines is enough to check it is stuck or not
        return fuzz_statuses[-constants.LIBFUZZER_LOG_STATUS_MAX_LINES :]


class Introspector:
    def __init__(self):
        pass

    def _cov_ft_not_increasing(self, fuzz_statuses, rounds):
        if rounds < 1 or rounds > len(fuzz_statuses) - 1:
            debug("Insufficient info to check the cov & ft not increasing.")
            return False

        not_increasing = True
        last_cov = fuzz_statuses[-1][1]
        last_ft = fuzz_statuses[-1][2]
        debug(f"Last cov: {last_cov}, Last ft: {last_ft}")
        for i in range(-rounds, -1, 1):
            if fuzz_statuses[i][1] != last_cov or fuzz_statuses[i][2] != last_ft:
                debug(
                    f"Round {i} changed: {fuzz_statuses[i][1]}, {fuzz_statuses[i][2]} vs {last_cov}, {last_ft}"
                )
                not_increasing = False
                break
            debug(
                f"Round {i} not changed: {fuzz_statuses[i][1]}, {fuzz_statuses[i][2]} vs {last_cov}, {last_ft}"
            )

        debug(f"final result: {not_increasing}")
        return not_increasing

    def is_fuzzing_stuck(self, fuzzer):
        """
        Check if the general fuzzing is stuck.
        """
        fuzz_statuses = LibfuzzerLogParser.parse_log(fuzzer.cfg.fuzz_log)
        info(f"Fuzzing status: {fuzz_statuses}")
        if (not fuzz_statuses) or (len(fuzz_statuses) == 0):
            warn("No fuzzing status found.")
            return None

        # check if the fuzzing is stuck -> cov & ft are not increasing in xxx rounds OR cov not increasing in yyy rounds
        if self._cov_ft_not_increasing(
            fuzz_statuses, constants.COV_FT_NOT_INCREASING_ROUNDS
        ):
            return True

        return False

    def _get_reached_sanitizer_hooked_funcs(self, isp_data):
        """
        Check the introspection data has triggered some sanitizer funcs or not.
        """
        reached_sanitizer_hooked_funcs = []
        for seed_sha, san_infos in isp_data["seed2SanitizerInfos"].items():
            if len(san_infos) > 0:
                reached_sanitizer_hooked_funcs.append(seed_sha)

        return reached_sanitizer_hooked_funcs
    def _get_sanitizer_dicts(self, isp_data, seeds):
        """
        Get the sanitizer dict files.
        """
        dicts = ["#"]

        # currently, we can directly get all possible dict values from all sanitizers
        arg_set = set([])
        for seed in seeds:
            san_infos = isp_data["seed2SanitizerInfos"][seed]
            for san_info in san_infos:
                args = san_info["args"]
                for arg in args:
                    arg_set.add(arg)

        count = 0
        for arg in arg_set:
            dicts.append(f"str_{count}=\"{util.escape_non_ascii(arg)}\"")
            count += 1

        return dicts

    def _gen_fuzzcfg_for_san_funcs(self, fuzzer, isp_data):
        focused_fuzz_cfgs = []

        # TODO: use related instrumentation
        focused_instrumentation = fuzzer.cfg.instrumentation_includes

        san2seeds = {}
        for seed_sha, san_infos in isp_data["seed2SanitizerInfos"].items():
            if len(san_infos) > 0:
                for san_info in san_infos:
                    k = san_info["sanitizerName"]
                    if k not in san2seeds:
                        san2seeds[k] = set([])
                    san2seeds[k].add(seed_sha)

        for san_ty, seeds in san2seeds.items():
            info(f"Sanitizer {san_ty} reached by seeds: {seeds}")
            # focused dict
            dicts = self._get_sanitizer_dicts(isp_data, seeds)

            # create a new fuzz cfg
            focused_fuzz_cfg = (
                fuzzer,
                dicts,
                seeds,
                focused_instrumentation,
                constants.FOCUSED_FUZZING_TOTAL_TIME,
            )
            focused_fuzz_cfgs.append(focused_fuzz_cfg)

        return focused_fuzz_cfgs

    def _gen_fuzzcfg_for_stuck_branches(self, fuzzer, isp_data, dump_class_dir):
        focused_fuzz_cfgs = []

        # dump stuckBranches into a file
        stuck_branch_file = os.path.join(fuzzer.cfg.work_dir, "stuck-branches.json")
        with open(stuck_branch_file, "w") as f:
            json.dump(isp_data["stuckBranches"], f, indent=2)

        # rank stuck branches & gen focused fuzzing cfg for top 5
        ranked_branch_file = os.path.join(fuzzer.cfg.work_dir, "ranked-branches.json")
        resp = util.query_until_get_lock(
            lambda: util.post_rankbranch(stuck_branch_file, ranked_branch_file)
        )
        if not util.check_rankbranch(resp):
            error("Rank stuck branches failed, try focused fuzzing in next round.")
            return focused_fuzz_cfgs

        top5_branch_info = []
        with open(stuck_branch_file, "r") as f:
            stuck_info = json.load(f)
            with open(ranked_branch_file, "r") as g:
                # info -> { "id" : distance }
                l_info = [(k, v) for k, v in json.load(g).items()]
                l_info.sort(key=lambda x: x[1])
                for i in range(min(5, len(l_info))):
                    edgeid = l_info[i][0]
                    top5_branch_info.append((edgeid, stuck_info[edgeid]))

        info(f"Top 5 stuck branches: {top5_branch_info}")

        for edgeid, branch_info in top5_branch_info:
            seeds = set([])
            for seed, ids in isp_data["seed2EdgeIds"].items():
                pred_ids = isp_data["execEdgeIdsOfStuckId"].get(str(int(edgeid)), [])

                #debug(f"Edgeid {edgeid} Seed {seed} {len(ids)} ids, pred_ids {len(pred_ids)}: {pred_ids}, has {len(set(ids).intersection(pred_ids))} ids.")
                # ids has intersection with pred_ids
                if len(set(ids).intersection(pred_ids)) > 0:
                    seeds.add(seed)
            
            if len(seeds) == 0:
                error(f"No seed found for edge {edgeid}, this may indicate a bug? warn and skip it.")
                continue

            # TODO: use related instrumentation
            focused_instrumentation = fuzzer.cfg.instrumentation_includes

            dicts = ["#"]
            with tempfile.NamedTemporaryFile() as tmp_dict:
                resp = util.query_until_get_lock(
                    lambda: util.post_gendict(
                        branch_info["className"],
                        branch_info["methodName"],
                        tmp_dict.name,
                        focused=True,
                    )
                )

                if not util.check_gendict(resp):
                    error("Gen dict failed, inherit the original fuzzer dict for it.")
                    with open(fuzzer.cfg.dict, "r") as f:
                        for line in f:
                            dicts.add(line.strip())
                else:
                    with open(tmp_dict.name, "r") as f:
                        for line in f:
                            dicts.append(line.strip())

            # create a new fuzz cfg
            focused_fuzz_cfg = (
                fuzzer,
                dicts,
                seeds,
                focused_instrumentation,
                constants.FOCUSED_FUZZING_TOTAL_TIME,
            )
            focused_fuzz_cfgs.append(focused_fuzz_cfg)

        return focused_fuzz_cfgs

    def introspect(self, fuzzer):
        """
        Introspect the general fuzzing process.
        """
        # 1. get introspection data from fuzzer
        # - result 1: stuck at a branch
        # - result 2: stuck at a sanitizer hooked function
        ispfuzzer = SelfIntrospectionFuzzer(fuzzer)
        isp_data = ispfuzzer.introspect()
        #
        # format of the introspection data
        #
        # { "allEdgeIds" : list(int) all edge ids,
        #   "seed2SanitizerInfos" : dict{seed : list(SanitizerInfo)} ,
        #   "seed2EdgeIds" : dict{seed name: list(int) edge ids} ,
        # }
        if not isp_data or isp_data == {}:
            info("No introspection data found.")
            return None

        focused_fuzz_cfgs = []
        reached_san_funcs = self._get_reached_sanitizer_hooked_funcs(isp_data)
        if len(reached_san_funcs) > 0:
            info("Sanitizer hooked functions reached, focus on its triggering.")
            # directly gen the fuzz cfg based on the func name
            try:
                focused_fuzz_cfgs = self._gen_fuzzcfg_for_san_funcs(fuzzer, isp_data)
            except Exception as e:
                error(f"Gen focused fuzzers for sanitizer funcs error: {e}")
                error(traceback.format_exc())

        # analyze the data via static analysis
        # find the ranked stuck branch & gen configurations
        info("Making fuzzing cfgs for stuck branches.")
        focused_fuzz_cfgs.extend(
            self._gen_fuzzcfg_for_stuck_branches(
                fuzzer, isp_data, ispfuzzer.cfg.dump_classes_dir
            )
        )

        return focused_fuzz_cfgs

    def is_focused_goal_reached(self, ffuzzer):
        """
        Check if the focused fuzzing reached the goal.
        """
        # TODO: this is optional
        return "optional feature, not implemented yet"
