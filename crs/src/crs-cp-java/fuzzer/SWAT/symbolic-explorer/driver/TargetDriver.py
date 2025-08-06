import base64
import copy
import json
import os
import signal
import struct
import subprocess
import tempfile
from contextlib import contextmanager
from enum import Enum

from driver.SymbolicStorage import SymbolicVar, DataTypes

from data.Database import Database
from driver.SymbolicStorage import SymbolicStorage
# import logging
#from log import logger, solution_logger, args_logger, constraints_logger
from log import GeneratedInputLogger, logger

from solver.SolverHandler import SATResult
from strategy.StrategyService import StrategyService
from mutf8 import decode_modified_utf8

import utils

class ExecutionStatus(Enum):
    SUCCESS = 1
    ERROR = 2
    TIMEOUT = 3
    CRASH = 4
    VIOLATION = 5


class Verdict(Enum):
    VIOLATION = "== ERROR"
    SAFE = "== OK"
    UNKNOWN = "== DONT-KNOW"
    NO_SYMBOLIC_VARS = "== NON-SYMBOLIC"


class Action(Enum):
    RANDOMNEXT = 1
    SYMBOLICNEXT = 2
    REPORTVERDICT = 3


class INPUTTYPE(Enum):
    RANDOM = 1
    SYMBOLIC = 2
    MAGIC = 3


class State:
    def __init__(self):
        self.verdict = Verdict.UNKNOWN


class TargetDriver:
    def __init__(self):
        self.state = State()
        self.sym_storage = SymbolicStorage()
        self.current_sym_storage = None
        self.collected_solutions = {}
        self.symbolic_storage = []
        self.endpoint_id = None
        self.is_debug = False
        self.args = None
        self.initvalue = None
        self.concolic_value_index = 0
        self.generated_input_logger = GeneratedInputLogger()

    def build_command(self, args, mem: int = 32) -> [str]:
        """Builds the Java command list with given parameters."""
        print(args)
        classpath = ''
        if len(args.classpath) > 0:
            classpath = ':'.join(args.classpath)
        cmd = [
            'java',
            '-cp',
            f'"{classpath}"',
            f'-Xmx{mem}g',
            f'-Dconfig.path={args.config}',
            f'-javaagent:{args.agent}',
            f"-Djava.library.path={args.z3dir}",
            #'-Dlogging.level=WARN',i
            '-ea',
            #'-jar',
            args.target
        ]
        print(' '.join(cmd))
        return cmd

    def unescape_unicode_string(self, s: [str]) -> [bytes]:
        #bs = list(bytes(s, "ascii"))
        bs = list(self.binary_encode(s))
        #return bs
        b_arr = []
        i = 0
        while (i < len(bs)):
            #logger.logger.info("LOOG: " + repr(bs[i:]))
            if bs[i] != ord('u'):
                b_arr.append(bs[i])
                i += 1
                continue
            # now bs[i] == 'u'
            if (len(bs) > i+4) and (bs[i+1] != ord('{') or bs[i+4] != ord('}')):
                b_arr.append(bs[i])
                i += 1
                continue
            # now bs[i:i+5] = u{xx}
            if (len(bs) > i+9) and (bs[i+6] != ord('{') or bs[i+9] != ord('}')):
                b_arr.append(bs[i])
                i += 1
                continue

            int_arr = [(int(bytes(bs[i+2:i+4]), 16)), (int(bytes(bs[i+7:i+9]), 16))]
            by_arr = bytes(int_arr)
            logger.logger.info("LOOG: " + repr(int_arr))
            logger.logger.info("LOOG: " + repr(by_arr))
            ss = decode_modified_utf8(by_arr)
            logger.logger.info(repr(ss))
            #bb = bytes(ss, 'ascii')
            bb = self.binary_encode(ss)
            logger.logger.info(repr(bb))
            aa = list(bb)
            logger.logger.info(repr(aa))
            b_arr += aa
            i += 10
            continue
        logger.logger.info(repr(b_arr))
        logger.logger.info(repr(bytes(b_arr)))
        return bytes(b_arr)

    def add_values(self, cmd: [str]) -> [str]:
        cmd = cmd.copy()
        """Adds the symbolic values to the Java command."""
        var_dict = {}
        arg_log_dict = {}
        #for key in self.sym_storage.vars.keys():
        #    v = self.sym_storage.vars[key]
        binary_inputs = []

        print(self.current_sym_storage.vars)

        int_var_count = 0
        for key in sorted(self.current_sym_storage.vars.keys()):
            v = self.current_sym_storage.vars[key]
            str_v = str(v)
            var_name = str_v.split(' ')[0]
            if v.dType == DataTypes.INT:
                print(f'{var_name} new: {v.newValue} old: {v.value}')
                if v.idx < 10:
                    value = int(v.value)
                    if not v.newValue is None:
                        value = int(v.newValue)
                        v.value = v.newValue
                    binary_inputs.append(struct.pack(">I", value))
                int_var_count += 1

            if not "STRING" in str_v:
                continue

            value = v.newValue
            first_exec = False
            if value is None:
                value = v.value
                first_exec = True
            else:
                v.newValue = v.value

            print(f'{var_name} new: {v.newValue} old: {v.value} first {first_exec}')

            #converted_value = self.binary_encode(self.unescape_unicode_string(value))
            #converted_value = self.binary_encode(value)
            converted_value = value
            print(f"converted value-2: {repr(converted_value)}")
            try:
                converted_value = utils.transform_mutf8_string_to_binstr(converted_value)
                print(f"converted value-2-1: {repr(converted_value)}")
                converted_bytes = bytes(converted_value, 'utf-8')
            except UnicodeDecodeError:
                return None
                #converted_bytes = converted_value


            print(f"converted value-2-2: {repr(converted_bytes)}")
            var_dict[key] = self.binary_encode(base64.b64encode(converted_bytes))
            arg_log_dict[key] = repr(var_dict[key])

            if first_exec:
                binary_inputs = []
                binary_inputs.append(converted_bytes)
            else:
                binary_inputs.append(converted_bytes)
            print("Logged value: " + arg_log_dict[key])

        print(binary_inputs)

        temp_fn = f"{tempfile.mkdtemp()}.sym"
        # use json format
        """
        json_dict = json.dumps(var_dict)
        with open(temp_fn, "wt") as f:
            print(json_dict)
            f.write(json_dict)
        """
        with open(temp_fn, "wb") as f:
            for binary in binary_inputs:
                f.write(binary)

        logger.args_logger.info(f'{json.dumps(arg_log_dict)}')
        #self.generated_input_logger.add_input(arg_log_dict)

        logger.logger.info(f"Tempfile is at: {temp_fn}")
        #input("PRESS ENTER to continue...")
        #for var in self.sym_storage.vars.values():
        #    if var.newValue is None:
        #        val = var.value
        #    else:
        #        val = var.newValue
        #        var.value = var.newValue
        #    cmd.append(f'"{val}"')
        cmd.append(temp_fn)
        return cmd

    def run_command_with_timeout(self, cmd: [str], timeout: int = 60) -> (ExecutionStatus, dict):
        """Executes the given command and returns the status and message."""

        logger.logger.info(f'[EXPLORER] Java Output Begin')
        try:
            stdout = []
            joined = ' '.join(cmd)
            print(cmd)
            print(joined)
            #with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
            #                      universal_newlines=True) as proc:
            #if (self.is_debug):
            #    input("PRESS ENTER to run the command: " + joined)
            with subprocess.Popen(joined, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1048576,
                                  universal_newlines=True, shell=True) as proc:

                for line in proc.stdout:
                    logger.logger.info(f'[EXECUTOR] --> {line.strip()}')
                    stdout.append(line)
            logger.logger.info(f'[EXPLORER] Java Output End')
            for l in stdout:
                if '*** java.lang.instrument ASSERTION FAILED ***' in l:
                    return ExecutionStatus.ERROR, stdout
            if proc.returncode == 0:
                return ExecutionStatus.SUCCESS, stdout
            else:
                for l in stdout:
                    if "java.lang.AssertionError" in l:
                        return ExecutionStatus.VIOLATION, stdout
                return ExecutionStatus.ERROR, stdout
        except subprocess.TimeoutExpired:
            return ExecutionStatus.TIMEOUT, stdout
        except Exception as e:
            logger.logger.critical(f'[EXPLORER] Exception: {e}')
            return ExecutionStatus.CRASH, str(e)

    def record_violation(self):
        """Records the violation in the database."""
        db = Database.instance()
        #db.add_violation(endpoint_id=self.endpoint_id, sym_vars=list(self.sym_storage.vars.values()))
        db.add_violation(endpoint_id=self.endpoint_id, sym_vars=list(self.current_sym_storage.vars.values()))

    def determine_next_step(self, status: ExecutionStatus, stdout: [str]) -> Action:
        """Determines the next step based on the execution status."""
        match status:
            case ExecutionStatus.SUCCESS:
                return Action.SYMBOLICNEXT
            case ExecutionStatus.VIOLATION:
                self.record_violation()
                logger.logger.info(f'[EXPLORER] Violation recorded!')
                return Action.SYMBOLICNEXT
            case ExecutionStatus.TIMEOUT:
                logger.logger.info(f'[EXPLORER] Timeout!')
                self.state.verdict = Verdict.UNKNOWN
                return Action.REPORTVERDICT
            case ExecutionStatus.CRASH:
                logger.logger.info(f'[EXPLORER] Crash!')
                self.state.verdict = Verdict.UNKNOWN
                return Action.REPORTVERDICT
            case ExecutionStatus.ERROR:
                logger.logger.info(f'[EXPLORER] Error!')
                self.state.verdict = Verdict.UNKNOWN
                return Action.REPORTVERDICT

        raise Exception(f'Unknown execution status: {status}')

    def binary_encode(self, s):
        if type(s) == type(""):
            arr = []
            for c in s:
                arr.append(ord(c))
            return bytes(arr)
        elif type(s) == type(b""):
            ret = ""
            for c in s:
                ret += chr(c)
            return ret

    def trim_constraint(self, c):
        str_arr = []
        prev_char = ''
        for i in range(len(c)):
            if c[i] == ' ':
                if prev_char == ' ':
                    pass
                else:
                    str_arr.append(c[i])
                prev_char = c[i]
            else:
                str_arr.append(c[i])
                prev_char = c[i]
        return ''.join(str_arr)

    def get_symbolic_variables_dict(self, symbolic_variables):
        # return dict
        d = {}
        # set variable count
        d['count'] = len(symbolic_variables)
        # for each variable
        for variables in symbolic_variables:
            dd = {}
            # set name and type
            dd['type'] = variables.variableType
            dd['name'] = variables.variableName
            # store to d by index
            d[variables.variableIndex] = dd

        # return all variables
        return d

    def null_strip(self, string):
        arr = []
        for c in string:
            if (c != '\x00'):
                arr.append(c)

        return ''.join(arr)

    def convert_value_to_stream(self, solution):
        prev_concolic_index = self.concolic_value_index
        remaining_concolic_values = self.initvalue[prev_concolic_index:]
        print(f"For type {solution['type']} start index {prev_concolic_index} values {repr(remaining_concolic_values)}")
        if solution['type'] == 'int':
            # FIXME: handle integer here
            self.concolic_value_index += 4
            return struct.pack('>i', int(solution['encoded_value']))
        elif solution['type'] == 'String':
            string = solution['encoded_value']

            # cut and update concolic value here
            concolic_value = None
            if len(remaining_concolic_values) > 0:
                cut_index = remaining_concolic_values.find('\x00')
                if cut_index == -1:
                    # end of stream input - flush!
                    self.concolic_value_index = len(self.initvalue)
                    concolic_value = remaining_concolic_values
                else:
                    # not end, cut!
                    self.concolic_value_index += (cut_index + 1)
                    concolic_value = remaining_concolic_values[:cut_index]
            else:
                concolic_value = 'A'

            # unconstrainted string
            if len(string) == 0:
                # put concolic value for the unconstrainted string
                return self.binary_encode(f"{concolic_value}\x00")

            converted_string = utils.transform_mutf8_string_to_binstr(string)
            if len(string) != 0 and len(converted_string) == 0:
                return self.binary_encode(self.null_strip(string) + "\x00")
            else:
                return self.binary_encode(self.null_strip(converted_string) + "\x00")
        else:
            print(f"Error: unknown type {solution['type']}")
            #assert False

    def convert_solution(self, variable_dict : dict, solution : dict) -> list:
        # example
        """
        {
            'I_2': {'encoded_value': '1', 'plain_value': 1, 'index': '2'},
            'Ljava/lang/String_4': {'encoded_value': '', 'plain_value': "", 'index': '4'},
            'Ljava/lang/String_5': {'encoded_value': '', 'plain_value': "", 'index': '5'},
            'Ljava/lang/String_3': {'encoded_value': 'x-evil-backdoor', 'plain_value': "x-evil-backdoor", 'index': '3'},
            'I_1': {'encoded_value': '13', 'plain_value': 13, 'index': '1'
        }
        """
        variables = copy.deepcopy(variable_dict)
        del variables['count']

        ret = {}
        ret['solution'] = []
        stream = []
        self.concolic_value_index = 0
        for k in sorted(variables.keys()):
            variable_info = variables[k]
            sol = solution.get(variable_info['name'])
            sol['name'] = variable_info['name']
            sol['type'] = variable_info['type']
            del sol['plain_value']
            ret['solution'].append(sol)
            stream.append(self.convert_value_to_stream(sol))

        ret['stream'] = repr(b''.join(stream))
        ret['initvalue'] = repr(self.initvalue)

        return ret

    def retrieve_solution(self):

        symbolic_variables = Database.instance().get_trace_symbolic_variables(self.endpoint_id)
        variables_dict = self.get_symbolic_variables_dict(symbolic_variables)

        possible_branches = StrategyService.select_branch(endpoint_id=self.endpoint_id)
        logger.logger.info(f'[EXPLORER] Found {len(possible_branches)} possible branches')

        symbolic_branches = [b for b in possible_branches if StrategyService.is_symbolic_branch(b)]
        logger.logger.info(f'[EXPLORER] Found {len(symbolic_branches)} symbolic branches')
        for b in symbolic_branches:
            new_constraint = {}
            for k in b.constraint.keys():
                str_constraint = b.constraint[k]
                new_constraint[k] = self.trim_constraint(str_constraint)
            b.constraint = new_constraint
            #logger.constraints_logger.info(b.constraint)
            #logger.constraints_logger.info(type(b.constraint))

        symbolic_vars = None
        sat = None
        branch_found = False

        sym_vars = []
        solutions = []

        for branch in possible_branches:
            if not StrategyService.is_symbolic_branch(branch):
                continue
            branch_found = True
            sat, sol = StrategyService.solve_branch(branch)
            logger.logger.info((sat, branch.constraint, sol))

            if sat == SATResult.SAT:
                #logger.constraints_logger.info(branch.inputs)
                symbolic_vars = branch.inputs
                sym_vars.append(branch.inputs)
                #var_names = [b.name for b in branch.inputs]
                #logger.constraints_logger.info(var_names)
                #logger.constraints_logger.info(sol)
                solutions.append(sol)
                #break

        #if not branch_found or sat == SATResult.UNSAT:
        if (len(solutions) == 0):
            if (len(self.symbolic_storage) == 0):
                self.state.verdict = Verdict.SAFE
                logger.logger.info(f'[EXPLORER] No symbolic branch found or UNSAT')
                return Action.REPORTVERDICT
            else:
                return Action.SYMBOLICNEXT

        #if sat == SATResult.UNKNOWN:
        #    logger.logger.info(f'[EXPLORER] SAT result is UNKNOWN')
        #    self.state.verdict = Verdict.UNKNOWN
        #    return Action.REPORTVERDICT

        #sol_viz = [f'{key}: {val["plain_value"]}' for key, val in sol.items()]
        logger.logger.info(f'[EXPLORER] Found new solution!')

        new_solutions = []
        for solution in solutions:
            new_solutions.append(self.convert_solution(variables_dict, solution))

        for new_solution in new_solutions:
            print('Solution converted: ')
            for entry in new_solution['solution']:
                print(entry)
            print(repr(new_solution['stream']))
            self.generated_input_logger.add_input(new_solution)

        #for solution in solutions:
        #    keys = solution.keys()
        #    print('Solution: ')
        #    for k in sorted(keys):
        #        print(solution[k])
        #logger.solution_logger.info(f'{solutions}')
        # self.sym_storage.register_vars(symbolic_vars)

        return Action.SYMBOLICNEXT


        for sol in solutions:
            and_result = True
            for k in sol.keys():
                if not k in self.collected_solutions:
                    self.collected_solutions[k] = []
                enc_value = sol[k]['encoded_value']
                if enc_value in self.collected_solutions[k]:
                    and_result = and_result and True
                else:
                    and_result = and_result and False
                    self.collected_solutions[k].append(enc_value)
            if not and_result:
                sym_storage = SymbolicStorage()
                sym_storage.register_vars(self.args.symbolicvars)
                sym_storage.init_values(self.initvalue)
                sym_storage.store_solution(sol)
                self.symbolic_storage.append(sym_storage)

        print("Stored Solutions:")
        for s in self.symbolic_storage:
            solution_dict = {}
            i = 0
            for k in s.vars.keys():
                logger.logger.info(f"{s.vars[k].newValue}")
                logger.logger.info(f"{s.vars[k]}")
                #input("PRESS ENTER")
                solution_value = s.vars[k].newValue
                decoded_solution_value = utils.transform_mutf8_string_to_binstr(s.vars[k].newValue)
                #print(repr(solution_value))
                #print(type(solution_value))
                #print(repr(decoded_solution_value))
                #print(type(decoded_solution_value))
                #input("PRESS ENTER TO CONTINUE...")
                solution_value = decoded_solution_value
                if type(solution_value) == type(''):
                    solution_value = self.binary_encode(solution_value)
                #solution_dict[str(i)] = repr(solution_value)
                solution_dict[s.vars[k].get_variable_name()] = repr(solution_value)
                i += 1
            self.generated_input_logger.add_input(solution_dict)

        #self.sym_storage.store_solution(sol)
        return Action.SYMBOLICNEXT

    def run(self, args):
        verdict = self.exec(args)
        logger.logger.info(f'[EXPLORER] Verdict: {verdict}')
        for item in self.generated_input_logger.inputs:
            print(item)
        self.generated_input_logger.write_to_file( \
                f'{args.logdir[0]}/generated_inputs.json')

        self.kill_current_process()

    def exec(self, args):

        """Runs the symbolic execution on the given testcase."""
        logger.logger.info(f'[EXPLORER] Beginning testcase analysis')
        if args.initvalue == None:
            self.initvalue = 'X'
        else:
            with open(args.initvalue, "rb") as f:
                data = f.read()
                self.initvalue = self.binary_encode(data)

        self.is_debug = args.debug
        self.args = args

        # Register symbolic variables
        self.sym_storage.register_vars(args.symbolicvars)
        self.sym_storage.init_values(self.initvalue)

        self.symbolic_storage.append(self.sym_storage)
        # Build the command to execute target
        base_cmd = self.build_command(args)
        print(' '.join(base_cmd))
        # Main execution loop
        executed = True
        while True:
            should_break = False
            current_symbolic_storage_size = len(self.symbolic_storage)
            #input(f"Press ENTER to run for {current_symbolic_storage_size}")
            for i in range(current_symbolic_storage_size):
                self.current_sym_storage = self.symbolic_storage.pop(0)

                # Add the symbolic values
                cmd = self.add_values(base_cmd)

                if cmd == None:
                    continue

                # Run the command
                #input(f"PRESS ENTER TO RUN {' '.join(cmd)}")
                status, output = self.run_command_with_timeout(cmd)
                # Determine the next step
                next_step = self.determine_next_step(status, output)
                # Select the (only!) endpoint
                print(next_step)
                #assert len(Database.instance().get_endpoint_ids()) == 1
                if len(Database.instance().get_endpoint_ids()) < 1:
                    if next_step == Action.REPORTVERDICT:
                        continue

                self.endpoint_id = Database.instance().get_endpoint_ids()[0]
                if next_step == Action.REPORTVERDICT:
                    should_break = True
                    break

                if next_step == Action.SYMBOLICNEXT:
                    logger.logger.info(f'[EXPLORER] Next step: SYMBOLIC EXPLORATION')
                    next_step = self.retrieve_solution()
                    if next_step == Action.REPORTVERDICT:
                        should_break = True
                        break

            if should_break:
                break
            if executed and args.one_step:
                print("Running one-step is finished")
                break
            executed = True

            """
            self.current_sym_storage = self.symbolic_storage.pop(0)
            # Add the symbolic values
            cmd = self.add_values(base_cmd)
            # Run the command
            #input(f"PRESS ENTER TO RUN {cmd}")
            status, output = self.run_command_with_timeout(cmd)
            # Determine the next step
            next_step = self.determine_next_step(status, output)
            # Select the (only!) endpoint
            assert len(Database.instance().get_endpoint_ids()) == 1
            self.endpoint_id = Database.instance().get_endpoint_ids()[0]
            if next_step == Action.REPORTVERDICT:
                break

            if next_step == Action.SYMBOLICNEXT:
                logger.logger.info(f'[EXPLORER] Next step: SYMBOLIC EXPLORATION')

                next_step = self.retrieve_solution()
                if next_step == Action.REPORTVERDICT:
                    break
            """

        logger.logger.info(f'[EXPLORER] Symbolic execution terminated')
        violations = Database.instance().get_violations(self.endpoint_id)
        logger.logger.info(f'[EXPLORER] Found {len(violations)} violations')
        if len(violations) > 0:
            for v in violations:
                logger.logger.info(f'[EXPLORER] Violation: {[vv.__str__() for vv in v]}')

    def kill_current_process(self):
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)  # Send termination signal
        # os.kill(pid, signal.SIGKILL)  # Use this for a more forceful kill if needed
